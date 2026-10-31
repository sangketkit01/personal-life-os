from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ledger', '0005_transaction_payment_history')]
    operations = [
        migrations.AddField(model_name='transaction', name='reporting_kind', field=models.CharField(
            max_length=20, default='AUTO', choices=[('AUTO', 'Use linked records / transaction direction'),
            ('INCOME', 'Earned income'), ('EXPENSE', 'Personal expense'), ('REIMBURSEMENT', 'Reimbursement'),
            ('LOAN', 'Loan principal'), ('INVESTMENT', 'Investment movement'), ('CARD_PAYMENT', 'Credit card settlement')])),
        migrations.AddField(model_name='categorybudget', name='currency', field=models.CharField(default='THB', max_length=5)),
        migrations.AlterUniqueTogether(name='categorybudget', unique_together={('user', 'category', 'period_month', 'currency')}),
    ]
