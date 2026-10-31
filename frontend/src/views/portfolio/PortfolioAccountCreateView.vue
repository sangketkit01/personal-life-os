<template>
  <div class="max-w-md mx-auto">
    <CreatePortfolioModal :is-open="true" inline @close="goBack" @created="handleCreated" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToastStore } from '../../stores/toast'
import { t } from '../../i18n'
import type { InvestmentPortfolio } from '../../types/portfolio'
import CreatePortfolioModal from '../../components/portfolio/CreatePortfolioModal.vue'
const router = useRouter(), toast = useToastStore(), navigating = ref(false)
function goBack() {
  if (!navigating.value) void router.push('/portfolio/accounts')
}
function handleCreated(portfolio: InvestmentPortfolio) {
  navigating.value = true
  toast.success(t('portfolio.ui.created', { name: portfolio.name }))
  void router.push(`/portfolio/accounts/${portfolio.id}`)
}
</script>
