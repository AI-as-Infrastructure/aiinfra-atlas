<template>
  <div class="inter-rater-page">
    <div class="container">
      <InterRaterDashboard />
    </div>
  </div>
</template>

<script>
import InterRaterDashboard from '@/components/InterRaterDashboard.vue'

export default {
  name: 'InterRaterPage',
  components: {
    InterRaterDashboard
  },
  meta: {
    title: 'Inter-rater Reliability - ATLAS'
  }
}
</script>

<style scoped>
.inter-rater-page {
  min-height: 100vh;
  padding-top: 2rem;
}

.container {
  max-width: 1200px;
}
</style>
