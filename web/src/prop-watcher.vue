<template>

</template>

<script setup>

const props = defineProps(['data'])
const emit = defineEmits(['change'])

watch(
  () => props.data,
  (value, oldValue) => {
    emit('change', [value, oldValue])
  }
)

</script>
