from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Account, Category, CategoryType, Transaction, TransactionType, TransactionSplit
from apps.finance.models import FinancialObligation, ObligationType, ObligationSubtype, FlowDirection, ObligationStatus


class AccountBalanceService:
    """
    Manages mathematical integrity of account balances across cash flow transactions.
    """

    @staticmethod
    @db_transaction.atomic
    def recalculate_account_balance(account: Account) -> Decimal:
        """
        Recalculates an account's real-time balance starting from initial_balance
        plus all inflows minus all outflows. Locks the account row during calculation.
        """
        locked_acc = Account.objects.select_for_update().get(id=account.id)

        inflows = Transaction.objects.filter(
            account=locked_acc,
            transaction_type=TransactionType.INFLOW
        ).aggregate(total=models.functions.Coalesce(models.Sum('gross_amount'), Decimal('0.00')))['total']

        outflows = Transaction.objects.filter(
            account=locked_acc,
            transaction_type=TransactionType.OUTFLOW
        ).aggregate(total=models.functions.Coalesce(models.Sum('gross_amount'), Decimal('0.00')))['total']

        new_balance = locked_acc.initial_balance + inflows - outflows
        locked_acc.current_balance = new_balance
        locked_acc.save(update_fields=['current_balance', 'updated_at'])
        account.current_balance = new_balance
        return new_balance

    @staticmethod
    @db_transaction.atomic
    def execute_transfer(
        user,
        source_account: Account,
        target_account: Account,
        amount: Decimal,
        transaction_date,
        title: str = "Transfer",
        notes: str = ""
    ) -> tuple[Transaction, Transaction]:
        """
        Executes an atomic transfer between two accounts by generating paired
        OUTFLOW and INFLOW transactions linked via transfer_peer.
        Acquires row-level pessimistic locks in deterministic ID order to prevent deadlocks.
        """
        if source_account.id == target_account.id:
            raise ValueError("Source and destination accounts must be different.")
        if amount <= Decimal('0.00'):
            raise ValueError("Transfer amount must be strictly positive.")
        if source_account.currency != target_account.currency:
            raise ValueError(f"Cross-currency transfers are not supported ({source_account.currency} to {target_account.currency}).")

        # Deadlock-free locking order
        first_id, second_id = sorted([source_account.id, target_account.id])
        Account.objects.select_for_update().get(id=first_id)
        Account.objects.select_for_update().get(id=second_id)

        # Refresh accounts under lock
        locked_source = Account.objects.get(id=source_account.id, user=user)
        locked_target = Account.objects.get(id=target_account.id, user=user)

        # Overdraft protection for non-credit accounts
        from apps.ledger.models import AccountType
        if locked_source.account_type != AccountType.CREDIT_CARD and locked_source.current_balance < amount:
            raise ValueError(
                f"Insufficient funds: {locked_source.name} has balance ฿{locked_source.current_balance:,.2f}, but transfer requires ฿{amount:,.2f}."
            )

        # 1. Outflow from source
        outflow_tx = Transaction.objects.create(
            user=user,
            account=locked_source,
            transaction_type=TransactionType.OUTFLOW,
            gross_amount=amount,
            net_amount=amount,
            title=title or f"Transfer to {locked_target.name}",
            notes=notes,
            transaction_date=transaction_date,
            transfer_destination=locked_target
        )

        # 2. Inflow into target
        inflow_tx = Transaction.objects.create(
            user=user,
            account=locked_target,
            transaction_type=TransactionType.INFLOW,
            gross_amount=amount,
            net_amount=amount,
            title=title or f"Transfer from {locked_source.name}",
            notes=notes,
            transaction_date=transaction_date,
            transfer_destination=locked_source,
            transfer_peer=outflow_tx
        )

        # 3. Link back
        outflow_tx.transfer_peer = inflow_tx
        outflow_tx.save(update_fields=['transfer_peer'])

        # 4. Update balances atomically with DB F() expressions
        Account.objects.filter(id=locked_source.id).update(
            current_balance=models.F('current_balance') - amount,
            updated_at=timezone.now()
        )
        Account.objects.filter(id=locked_target.id).update(
            current_balance=models.F('current_balance') + amount,
            updated_at=timezone.now()
        )

        locked_source.refresh_from_db(fields=['current_balance', 'updated_at'])
        locked_target.refresh_from_db(fields=['current_balance', 'updated_at'])
        source_account.current_balance = locked_source.current_balance
        target_account.current_balance = locked_target.current_balance

        return outflow_tx, inflow_tx


class BillSplitService:
    """
    Orchestrates group expense splitting and bi-directional integration with Financial Radar.
    Supports both classic equal/custom splits and Harntung itemized receipt splits.
    """

    @staticmethod
    def calculate_harntung_shares(
        gross_amount: Decimal,
        items: list[dict],
        participants: list[dict],
        service_charge_pct: Decimal = Decimal('0.00'),
        vat_pct: Decimal = Decimal('0.00'),
        payer_name: str = "Me"
    ) -> tuple[Decimal, list[dict]]:
        """
        Calculates itemized Harntung splits with proportional service charge and VAT.
        Each item is divided equally among its tagged consumers.
        Returns (payer_net_share, friend_splits).
        """
        raw_shares = {p['name']: Decimal('0.00') for p in participants}
        items_by_person = {p['name']: [] for p in participants}

        subtotal = Decimal('0.00')
        for item in items:
            item_price = Decimal(str(item.get('price', '0.00')))
            qty = Decimal(str(item.get('quantity', 1)))
            item_total = item_price * qty
            subtotal += item_total

            consumers = item.get('consumers', [])
            if not consumers:
                consumers = [p['name'] for p in participants]

            consumer_count = Decimal(str(len(consumers)))
            share_per_person = (item_total / consumer_count).quantize(Decimal('0.01'))

            for c_name in consumers:
                if c_name not in raw_shares:
                    raw_shares[c_name] = Decimal('0.00')
                    items_by_person[c_name] = []
                raw_shares[c_name] += share_per_person
                items_by_person[c_name].append({
                    'name': item.get('name', 'Item'),
                    'price': float(item_price),
                    'quantity': float(qty),
                    'consumer_count': len(consumers),
                    'share': float(share_per_person)
                })

        sc_rate = Decimal(str(service_charge_pct)) / Decimal('100.0')
        vat_rate = Decimal(str(vat_pct)) / Decimal('100.0')
        effective_multiplier = (Decimal('1.0') + sc_rate) * (Decimal('1.0') + vat_rate)

        final_shares = {}
        for name, raw in raw_shares.items():
            final_shares[name] = (raw * effective_multiplier).quantize(Decimal('0.01'))

        # Adjust any rounding difference against gross_amount to maintain double-entry parity
        calculated_total = sum(final_shares.values(), Decimal('0.00'))
        if gross_amount > Decimal('0.00') and calculated_total > Decimal('0.00'):
            diff = gross_amount - calculated_total
            if payer_name in final_shares:
                final_shares[payer_name] += diff
            elif participants:
                final_shares[participants[0]['name']] += diff

        payer_net = final_shares.get(payer_name, Decimal('0.00'))

        friend_splits = []
        for p in participants:
            name = p['name']
            if name == payer_name:
                continue
            friend_splits.append({
                'counterparty_name': name,
                'counterparty_contact': p.get('contact', ''),
                'amount': final_shares.get(name, Decimal('0.00')),
                'notes': p.get('notes', ''),
                'items_detail': items_by_person.get(name, [])
            })

        return payer_net, friend_splits

    @staticmethod
    @db_transaction.atomic
    def create_split_transaction(
        user,
        account: Account,
        category: Category,
        gross_amount: Decimal,
        net_amount: Decimal,
        title: str,
        transaction_date,
        splits_data: list[dict],
        auto_create_radar_debtors: bool = True,
        notes: str = "",
        split_metadata: dict = None,
        workspace_project=None
    ) -> Transaction:
        """
        Creates a master transaction with child splits.
        Acquires row lock on account and ensures split sums do not exceed gross amount.
        Supports Harntung itemized calculation and stores item breakdown per debtor.
        """
        if gross_amount <= Decimal('0.00'):
            raise ValueError("Gross amount must be strictly positive.")

        split_metadata = split_metadata or {}

        # If Harntung itemized payload is provided in split_metadata
        if split_metadata.get('items') and split_metadata.get('participants'):
            sc_pct = Decimal(str(split_metadata.get('service_charge_pct', '0.00')))
            vat_pct = Decimal(str(split_metadata.get('vat_pct', '0.00')))
            payer_name = split_metadata.get('payer_name', 'Me')
            payer_net, harntung_splits = BillSplitService.calculate_harntung_shares(
                gross_amount=gross_amount,
                items=split_metadata['items'],
                participants=split_metadata['participants'],
                service_charge_pct=sc_pct,
                vat_pct=vat_pct,
                payer_name=payer_name
            )
            net_amount = payer_net
            splits_data = harntung_splits

        split_sum = Decimal('0.00')
        for s in splits_data:
            s_val = Decimal(str(s.get('amount', 0)))
            if s_val <= Decimal('0.00'):
                raise ValueError("Each split share amount must be strictly positive.")
            split_sum += s_val

        if split_sum > gross_amount:
            raise ValueError(f"Total split shares ({split_sum}) cannot exceed total bill amount ({gross_amount}).")

        # Auto-adjust net_amount if not explicitly matching
        if gross_amount != (net_amount + split_sum):
            net_amount = gross_amount - split_sum

        # Lock account row and prevent negative balance for non-credit accounts
        from apps.ledger.models import AccountType
        locked_account = Account.objects.select_for_update().get(id=account.id, user=user)
        if locked_account.account_type != AccountType.CREDIT_CARD and locked_account.current_balance < gross_amount:
            raise ValueError(
                f"Insufficient funds: {locked_account.name} has balance ฿{locked_account.current_balance:,.2f}, but transaction requires ฿{gross_amount:,.2f}."
            )

        tx = Transaction.objects.create(
            user=user,
            account=locked_account,
            transaction_type=TransactionType.OUTFLOW,
            category=category,
            gross_amount=gross_amount,
            net_amount=net_amount,
            title=title,
            notes=notes,
            transaction_date=transaction_date,
            is_split=True,
            split_metadata=split_metadata,
            workspace_project=workspace_project
        )

        # Update account balance atomically
        Account.objects.filter(id=locked_account.id).update(
            current_balance=models.F('current_balance') - gross_amount,
            updated_at=timezone.now()
        )
        locked_account.refresh_from_db(fields=['current_balance', 'updated_at'])
        account.current_balance = locked_account.current_balance

        # Create child splits and optional Financial Radar Debtors
        for s in splits_data:
            s_amount = Decimal(str(s['amount']))
            c_name = s.get('counterparty_name', 'Friend').strip()
            c_contact = s.get('counterparty_contact', '').strip()
            s_notes = s.get('notes', '').strip()
            s_items = s.get('items_detail', [])

            radar_obligation = None
            if auto_create_radar_debtors:
                # Auto-create DEBT in Financial Radar with direction=INFLOW (Debtor owes us)
                radar_obligation = FinancialObligation.objects.create(
                    user=user,
                    title=f"{c_name} - {title}",
                    type=ObligationType.DEBT,
                    subtype=ObligationSubtype.INFORMAL_BORROW,
                    direction=FlowDirection.INFLOW,
                    amount=s_amount,
                    currency=locked_account.currency,
                    status=ObligationStatus.ACTIVE,
                    metadata={
                        'counterparty': c_name,
                        'contact': c_contact,
                        'promptpay': c_contact,
                        'origin_bill': title,
                        'origin_transaction_id': str(tx.id),
                        'is_flexible': True,
                        'items_detail': s_items,
                        'notes': f"Auto-generated from Split Bill '{title}' ({transaction_date}). {s_notes}".strip()
                    }
                )

            TransactionSplit.objects.create(
                transaction=tx,
                counterparty_name=c_name,
                counterparty_contact=c_contact,
                amount=s_amount,
                is_settled=False,
                debtor_obligation=radar_obligation,
                notes=s_notes,
                items_detail=s_items
            )

        return tx

    @staticmethod
    @db_transaction.atomic
    def settle_split(
        split: TransactionSplit,
        deposit_account: Account,
        settlement_date=None,
        settlement_title: str = ""
    ) -> Transaction:
        """
        Settles a pending split when a friend transfers repayment money back.
        Uses row-level locking to prevent double settlement race conditions.
        """
        locked_split = TransactionSplit.objects.select_for_update().get(id=split.id)
        if locked_split.is_settled:
            raise ValueError("This split item is already settled.")

        locked_account = Account.objects.select_for_update().get(
            id=deposit_account.id,
            user=locked_split.transaction.user
        )

        now_date = settlement_date or timezone.now().date()
        title = settlement_title or f"Split Repayment: {locked_split.counterparty_name} ({locked_split.transaction.title})"

        # Find or use Debt Settlement system category
        debt_category = Category.objects.filter(
            name="Debt Settlement",
            category_type=CategoryType.INCOME
        ).first()

        # Determine actual settlement amount (respect partial payments on debtor obligation)
        settle_amount = locked_split.amount
        debtor_ob = None
        if locked_split.debtor_obligation_id:
            from apps.finance.models import FinancialObligation, PaymentHistory
            debtor_ob = FinancialObligation.objects.select_for_update().get(id=locked_split.debtor_obligation_id)
            debtor_meta = debtor_ob.metadata or {}
            rem = debtor_meta.get('remaining_balance')
            if rem is not None:
                settle_amount = Decimal(str(rem))

        if settle_amount <= Decimal('0.00'):
            locked_split.is_settled = True
            locked_split.settled_at = timezone.now()
            locked_split.save(update_fields=['is_settled', 'settled_at'])
            return None

        # 1. Create Inflow Transaction
        inflow_tx = Transaction.objects.create(
            user=locked_split.transaction.user,
            account=locked_account,
            transaction_type=TransactionType.INFLOW,
            category=debt_category,
            gross_amount=settle_amount,
            net_amount=settle_amount,
            title=title,
            notes=f"Repayment for split on '{locked_split.transaction.title}' ({locked_split.transaction.transaction_date})",
            transaction_date=now_date
        )

        # 2. Deposit funds into account atomically
        Account.objects.filter(id=locked_account.id).update(
            current_balance=models.F('current_balance') + settle_amount,
            updated_at=timezone.now()
        )
        locked_account.refresh_from_db(fields=['current_balance', 'updated_at'])
        deposit_account.current_balance = locked_account.current_balance

        # 3. Mark split as settled
        locked_split.is_settled = True
        locked_split.settled_at = timezone.now()
        locked_split.settlement_transaction = inflow_tx
        locked_split.save(update_fields=['is_settled', 'settled_at', 'settlement_transaction'])

        split.is_settled = True
        split.settled_at = locked_split.settled_at
        split.settlement_transaction = inflow_tx

        # 4. If linked to Financial Radar, close the debtor obligation and link payment history
        if debtor_ob:
            from apps.finance.models import PaymentHistory
            debtor_ob.status = ObligationStatus.COMPLETED
            debtor_meta = debtor_ob.metadata or {}
            debtor_meta['remaining_balance'] = 0.0
            debtor_ob.metadata = debtor_meta
            debtor_ob.save(update_fields=['status', 'metadata'])

            ph = PaymentHistory.objects.create(
                user=locked_split.transaction.user,
                obligation=debtor_ob,
                paid_amount=settle_amount,
                note=f"Settled via Cash Flow Ledger into {locked_account.name}"
            )
            inflow_tx.payment_history = ph
            inflow_tx.obligation = debtor_ob
            inflow_tx.save(update_fields=['payment_history', 'obligation'])

        return inflow_tx


class CategorySeedService:
    """
    Seeds default system categories if absent.
    """

    SYSTEM_CATEGORIES = [
        # Expenses
        ("Food & Dining", CategoryType.EXPENSE, "Utensils", [
            ("Groceries", "ShoppingBag"),
            ("Restaurants", "UtensilsCrossed"),
            ("Coffee & Drinks", "Coffee"),
            ("Food Delivery", "Truck")
        ]),
        ("Transportation", CategoryType.EXPENSE, "Car", [
            ("Public Transit / BTS", "Train"),
            ("Fuel / Gas", "Fuel"),
            ("Ride Hailing / Taxi", "CarFront"),
            ("Vehicle Maintenance", "Wrench")
        ]),
        ("Housing & Utilities", CategoryType.EXPENSE, "Home", [
            ("Electricity & Water", "Zap"),
            ("Internet & Mobile", "Wifi"),
            ("Rent & Maintenance", "Building")
        ]),
        ("Technology & Dev", CategoryType.EXPENSE, "Code", [
            ("Cloud & Servers", "Server"),
            ("Software Subscriptions", "Layers"),
            ("Hardware & Gadgets", "Laptop")
        ]),
        ("Shopping & Leisure", CategoryType.EXPENSE, "ShoppingBag", [
            ("Clothing & Apparel", "Shirt"),
            ("Entertainment & Gaming", "Gamepad2"),
            ("Travel & Hotels", "Plane")
        ]),
        ("Healthcare & Fitness", CategoryType.EXPENSE, "Activity", [
            ("Gym & Sports", "Dumbbell"),
            ("Pharmacy & Medical", "HeartPulse")
        ]),
        ("Obligations & Loans", CategoryType.EXPENSE, "Landmark", [
            ("Installment Contracts", "Car"),
            ("BNPL Settlements", "ShoppingBag"),
            ("Debt Repayment", "HandCoins")
        ]),
        # Incomes
        ("Salary & Wages", CategoryType.INCOME, "Briefcase", [
            ("Base Salary", "Briefcase"),
            ("Bonus & Incentive", "Award")
        ]),
        ("Freelance & Business", CategoryType.INCOME, "Laptop", [
            ("Dev Contracts", "Code"),
            ("Consulting & Services", "FileCode")
        ]),
        ("Investment & Dividends", CategoryType.INCOME, "TrendingUp", [
            ("Stock Dividends", "Coins"),
            ("Capital Gains", "LineChart"),
            ("Interest", "Percent")
        ]),
        ("Debt Settlement", CategoryType.INCOME, "HandCoins", [
            ("Repayment from Debtor", "UserCheck")
        ]),
        ("Other Income", CategoryType.INCOME, "CircleDot", [])
    ]

    @classmethod
    def seed_defaults(cls):
        """
        Seeds standard English categories safely with idempotency.
        """
        for parent_name, cat_type, icon, subcategories in cls.SYSTEM_CATEGORIES:
            parent, _ = Category.objects.get_or_create(
                name=parent_name,
                category_type=cat_type,
                user=None,
                parent=None,
                defaults={'icon': icon, 'is_system': True}
            )

            for sub_name, sub_icon in subcategories:
                Category.objects.get_or_create(
                    name=sub_name,
                    category_type=cat_type,
                    user=None,
                    parent=parent,
                    defaults={'icon': sub_icon, 'is_system': True}
                )
