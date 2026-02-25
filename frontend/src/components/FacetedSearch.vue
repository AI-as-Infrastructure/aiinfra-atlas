<template>
  <div v-if="facets.length > 0" class="faceted-search">
    <div class="faceted-search-header" @click="togglePanel">
      <span class="faceted-search-title">Advanced Filters</span>
      <span class="faceted-search-toggle">{{ isExpanded ? '&#9660;' : '&#9654;' }}</span>
    </div>
    <div v-show="isExpanded" class="faceted-search-body">
      <div v-for="facet in facets" :key="facet.field" class="facet-group">
        <!-- Text facet: searchable dropdown -->
        <div v-if="facet.type === 'text'" class="facet-control">
          <label class="facet-label">{{ facet.label }}</label>
          <div class="facet-text-control">
            <div class="select is-small is-fullwidth">
              <select
                :value="getFilterValue(facet.field)"
                @change="setFilterValue(facet.field, $event.target.value)"
              >
                <option value="">All</option>
                <option
                  v-for="val in filteredTextOptions(facet)"
                  :key="val"
                  :value="val"
                >
                  {{ val }}
                </option>
              </select>
            </div>
            <input
              v-if="facet.values && facet.values.length > 10"
              class="input is-small facet-search-input"
              type="text"
              placeholder="Search..."
              :value="getSearchTerm(facet.field)"
              @input="setSearchTerm(facet.field, $event.target.value)"
            />
            <button
              v-if="getFilterValue(facet.field)"
              class="button is-small facet-clear-btn"
              @click="clearFilter(facet.field)"
              title="Clear filter"
            >
              x
            </button>
          </div>
        </div>

        <!-- Date range facet: from/to date inputs -->
        <div v-if="facet.type === 'date_range'" class="facet-control">
          <label class="facet-label">{{ facet.label }}</label>
          <div class="facet-date-range">
            <input
              class="input is-small"
              type="date"
              :min="facet.min"
              :max="facet.max"
              :value="getDateFrom(facet.field)"
              @change="setDateFrom(facet.field, $event.target.value)"
              placeholder="From"
            />
            <span class="date-separator">to</span>
            <input
              class="input is-small"
              type="date"
              :min="facet.min"
              :max="facet.max"
              :value="getDateTo(facet.field)"
              @change="setDateTo(facet.field, $event.target.value)"
              placeholder="To"
            />
            <button
              v-if="getDateFrom(facet.field) || getDateTo(facet.field)"
              class="button is-small facet-clear-btn"
              @click="clearDateRange(facet.field)"
              title="Clear date range"
            >
              x
            </button>
          </div>
        </div>

        <!-- Keyword facet: multi-select checkboxes -->
        <div v-if="facet.type === 'keyword'" class="facet-control">
          <label class="facet-label">{{ facet.label }}</label>
          <div class="facet-keyword-control">
            <div
              v-for="val in visibleKeywords(facet)"
              :key="val"
              class="facet-keyword-item"
            >
              <label class="checkbox is-small">
                <input
                  type="checkbox"
                  :checked="isKeywordSelected(facet.field, val)"
                  @change="toggleKeyword(facet.field, val)"
                />
                <span class="keyword-label">{{ val }}</span>
              </label>
            </div>
            <button
              v-if="facet.values && facet.values.length > 8"
              class="button is-small is-text facet-show-more"
              @click="toggleShowAll(facet.field)"
            >
              {{ isShowingAll(facet.field) ? 'Show less' : `Show all (${facet.values.length})` }}
            </button>
            <button
              v-if="getSelectedKeywords(facet.field).length > 0"
              class="button is-small facet-clear-btn"
              @click="clearKeywords(facet.field)"
              title="Clear keywords"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <!-- Clear all button -->
      <div v-if="hasActiveFilters" class="facet-actions">
        <button class="button is-small is-light" @click="clearAll">
          Clear All Filters
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  facets: {
    type: Array,
    required: true,
    default: () => []
  }
})

const emit = defineEmits(['filter-change'])

// Panel state
const isExpanded = ref(true)

// Filter state: { field: value } for text, { field: { from, to } } for date, { field: [values] } for keyword
const filterState = ref({})

// Search terms for text facets with many options
const searchTerms = ref({})

// Track which keyword facets show all values
const showAllState = ref({})

// --- Panel toggle ---
function togglePanel() {
  isExpanded.value = !isExpanded.value
}

// --- Text facet methods ---
function getFilterValue(field) {
  return filterState.value[field] || ''
}

function setFilterValue(field, value) {
  if (value) {
    filterState.value[field] = value
  } else {
    delete filterState.value[field]
  }
  emitFilters()
}

function getSearchTerm(field) {
  return searchTerms.value[field] || ''
}

function setSearchTerm(field, term) {
  searchTerms.value[field] = term
}

function filteredTextOptions(facet) {
  if (!facet.values) return []
  const term = getSearchTerm(facet.field)
  if (!term) return facet.values
  const lower = term.toLowerCase()
  return facet.values.filter(v => v.toLowerCase().includes(lower))
}

function clearFilter(field) {
  delete filterState.value[field]
  searchTerms.value[field] = ''
  emitFilters()
}

// --- Date range facet methods ---
function getDateFrom(field) {
  const val = filterState.value[field]
  return val && typeof val === 'object' ? val.from || '' : ''
}

function getDateTo(field) {
  const val = filterState.value[field]
  return val && typeof val === 'object' ? val.to || '' : ''
}

function setDateFrom(field, value) {
  if (!filterState.value[field] || typeof filterState.value[field] !== 'object') {
    filterState.value[field] = {}
  }
  if (value) {
    filterState.value[field] = { ...filterState.value[field], from: value }
  } else {
    const { from, ...rest } = filterState.value[field]
    filterState.value[field] = Object.keys(rest).length > 0 ? rest : undefined
    if (!filterState.value[field]) delete filterState.value[field]
  }
  emitFilters()
}

function setDateTo(field, value) {
  if (!filterState.value[field] || typeof filterState.value[field] !== 'object') {
    filterState.value[field] = {}
  }
  if (value) {
    filterState.value[field] = { ...filterState.value[field], to: value }
  } else {
    const { to, ...rest } = filterState.value[field]
    filterState.value[field] = Object.keys(rest).length > 0 ? rest : undefined
    if (!filterState.value[field]) delete filterState.value[field]
  }
  emitFilters()
}

function clearDateRange(field) {
  delete filterState.value[field]
  emitFilters()
}

// --- Keyword facet methods ---
function getSelectedKeywords(field) {
  const val = filterState.value[field]
  return Array.isArray(val) ? val : []
}

function isKeywordSelected(field, keyword) {
  return getSelectedKeywords(field).includes(keyword)
}

function toggleKeyword(field, keyword) {
  const current = getSelectedKeywords(field)
  if (current.includes(keyword)) {
    const updated = current.filter(k => k !== keyword)
    if (updated.length > 0) {
      filterState.value[field] = updated
    } else {
      delete filterState.value[field]
    }
  } else {
    filterState.value[field] = [...current, keyword]
  }
  emitFilters()
}

function clearKeywords(field) {
  delete filterState.value[field]
  emitFilters()
}

function visibleKeywords(facet) {
  if (!facet.values) return []
  if (isShowingAll(facet.field) || facet.values.length <= 8) {
    return facet.values
  }
  return facet.values.slice(0, 8)
}

function isShowingAll(field) {
  return !!showAllState.value[field]
}

function toggleShowAll(field) {
  showAllState.value[field] = !showAllState.value[field]
}

// --- Computed ---
const hasActiveFilters = computed(() => {
  return Object.keys(filterState.value).length > 0
})

// --- Emit combined filter state ---
function emitFilters() {
  // Build a structured filter object for the API
  const facetFilters = {}
  for (const facet of props.facets) {
    const value = filterState.value[facet.field]
    if (value === undefined || value === null || value === '') continue

    if (facet.type === 'text' && typeof value === 'string') {
      facetFilters[facet.field] = { type: 'text', value }
    } else if (facet.type === 'date_range' && typeof value === 'object' && !Array.isArray(value)) {
      if (value.from || value.to) {
        facetFilters[facet.field] = { type: 'date_range', ...value }
      }
    } else if (facet.type === 'keyword' && Array.isArray(value) && value.length > 0) {
      facetFilters[facet.field] = { type: 'keyword', values: value }
    }
  }

  emit('filter-change', facetFilters)
}

// --- Clear all filters ---
function clearAll() {
  filterState.value = {}
  searchTerms.value = {}
  emitFilters()
}

// Reset filters when facets config changes
watch(() => props.facets, () => {
  filterState.value = {}
  searchTerms.value = {}
  showAllState.value = {}
  emitFilters()
}, { deep: true })
</script>

<style scoped>
.faceted-search {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.faceted-search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #e0e0e0;
}

.faceted-search-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #333;
}

.faceted-search-toggle {
  font-size: 0.7rem;
  color: #666;
}

.faceted-search-body {
  padding: 0.75rem;
}

.facet-group {
  margin-bottom: 0.75rem;
}

.facet-group:last-child {
  margin-bottom: 0;
}

.facet-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: #555;
  margin-bottom: 0.25rem;
}

.facet-control {
  margin-bottom: 0.5rem;
}

/* Text facet */
.facet-text-control {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.facet-text-control .select {
  flex: 1;
}

.facet-search-input {
  max-width: 120px;
}

/* Date range facet */
.facet-date-range {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  flex-wrap: wrap;
}

.facet-date-range .input {
  flex: 1;
  min-width: 120px;
}

.date-separator {
  font-size: 0.8rem;
  color: #888;
  padding: 0 0.15rem;
}

/* Keyword facet */
.facet-keyword-control {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  align-items: center;
}

.facet-keyword-item {
  font-size: 0.8rem;
}

.facet-keyword-item .checkbox {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.keyword-label {
  font-size: 0.8rem;
  color: #333;
}

/* Buttons */
.facet-clear-btn {
  padding: 0 0.4rem !important;
  font-size: 0.75rem !important;
  height: 1.75rem !important;
  border: 1px solid #ccc !important;
  background: #fff !important;
  color: #666 !important;
  cursor: pointer;
}

.facet-clear-btn:hover {
  background: #f0f0f0 !important;
  color: #333 !important;
}

.facet-show-more {
  font-size: 0.75rem !important;
  color: #555 !important;
  text-decoration: underline;
  padding: 0 !important;
}

.facet-actions {
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #e0e0e0;
}
</style>
