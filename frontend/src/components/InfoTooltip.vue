<template>
  <span
    ref="trigger"
    class="info-tooltip"
    tabindex="0"
    role="note"
    :aria-label="text"
    @mouseenter="show"
    @mouseleave="hide"
    @focus="show"
    @blur="hide"
    @keydown.esc="hide"
  >ⓘ<span
      v-if="visible"
      ref="bubble"
      class="info-tooltip-bubble"
      :class="{ 'is-ready': ready }"
      :style="position"
    >{{ text }}</span></span>
</template>

<script setup>
// Rubric and fault definitions. Rendered by the app rather than left to the
// browser's native title behaviour, which is untestable and did not appear in
// Chrome (#70). Fixed positioning escapes the overflow:hidden ancestors that
// clip the citation card (#71).
import { ref, nextTick, onBeforeUnmount } from 'vue'

defineProps({
  text: { type: String, required: true }
})

const MARGIN = 8

const trigger = ref(null)
const bubble = ref(null)
const visible = ref(false)
const ready = ref(false)
const position = ref({})

async function show() {
  visible.value = true
  ready.value = false
  await nextTick()
  if (!trigger.value || !bubble.value) return

  const anchor = trigger.value.getBoundingClientRect()
  const box = bubble.value.getBoundingClientRect()

  // Centre on the trigger, then clamp so neither edge leaves the viewport.
  let left = anchor.left + anchor.width / 2 - box.width / 2
  left = Math.max(MARGIN, Math.min(left, window.innerWidth - box.width - MARGIN))

  // Prefer below; flip above when the bubble would run off the bottom.
  const below = anchor.bottom + MARGIN
  const top = below + box.height > window.innerHeight - MARGIN
    ? Math.max(MARGIN, anchor.top - box.height - MARGIN)
    : below

  position.value = { left: `${Math.round(left)}px`, top: `${Math.round(top)}px` }
  ready.value = true
}

function hide() {
  visible.value = false
  ready.value = false
}

onBeforeUnmount(hide)
</script>

<style scoped>
.info-tooltip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* #70: the old 12px glyph was too small to hover reliably. */
  min-width: 18px;
  min-height: 18px;
  margin-left: 0.25rem;
  color: #6c757d;
  font-size: 14px;
  line-height: 1;
  cursor: help;
  vertical-align: middle;
}

.info-tooltip:focus-visible {
  outline: 2px solid #363636;
  outline-offset: 2px;
  border-radius: 50%;
}

.info-tooltip-bubble {
  position: fixed;
  z-index: 2000;
  max-width: min(320px, calc(100vw - 16px));
  padding: 0.5rem 0.65rem;
  background: #363636;
  color: #fff;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
  font-size: 12px;
  font-weight: 400;
  line-height: 1.4;
  text-align: left;
  white-space: normal;
  cursor: default;
  /* Hidden until measured, so it never paints at the wrong place first. */
  opacity: 0;
  pointer-events: none;
}

.info-tooltip-bubble.is-ready {
  opacity: 1;
}
</style>
