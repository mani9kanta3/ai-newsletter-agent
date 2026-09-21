import { configureStore, createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { apiRequest } from './api'

export const loadRuns = createAsyncThunk('newsletters/list', async () =>
  apiRequest('/runs')
)
export const openRun = createAsyncThunk('newsletters/open', async (id) =>
  apiRequest('/runs/' + id)
)
export const refreshRun = createAsyncThunk('newsletters/refresh', async (id) =>
  apiRequest('/runs/' + id)
)

export const startRun = createAsyncThunk(
  'newsletters/start',
  async (data, { dispatch }) => {
    const run = await apiRequest('/runs', data)
    dispatch(loadRuns())
    return run
  }
)

export const sendDecision = createAsyncThunk(
  'newsletters/decision',
  async (data, { getState, dispatch }) => {
    const id = getState().newsletters.current.id
    const run = await apiRequest('/runs/' + id + '/decision', data)
    dispatch(loadRuns())
    return run
  }
)

const newslettersSlice = createSlice({
  name: 'newsletters',
  initialState: {
    current: null,
    selectedId: '',
    runs: [],
    loading: false,
    submitting: false,
    error: ''
  },
  reducers: {
    newNewsletter(state) {
      state.current = null
      state.selectedId = ''
      state.error = ''
      state.loading = false
    }
  },
  extraReducers: (builder) => {
    builder.addCase(loadRuns.fulfilled, (state, action) => {
      state.runs = action.payload
    })
    builder.addCase(loadRuns.rejected, (state, action) => {
      state.error = action.error.message
    })
    builder.addCase(openRun.pending, (state, action) => {
      state.selectedId = action.meta.arg
      state.current = null
      state.loading = true
      state.error = ''
    })
    builder.addCase(openRun.fulfilled, (state, action) => {
      if (state.selectedId !== action.meta.arg) return
      state.current = action.payload
      state.loading = false
    })
    builder.addCase(openRun.rejected, (state, action) => {
      if (state.selectedId !== action.meta.arg) return
      state.loading = false
      state.error = action.error.message
    })
    builder.addCase(refreshRun.fulfilled, (state, action) => {
      if (state.selectedId !== action.meta.arg) return
      state.current = action.payload
      state.error = ''
    })
    builder.addCase(refreshRun.rejected, (state, action) => {
      if (state.selectedId === action.meta.arg) state.error = action.error.message
    })
    builder.addCase(startRun.pending, (state) => {
      state.submitting = true
      state.error = ''
    })
    builder.addCase(startRun.fulfilled, (state, action) => {
      state.current = action.payload
      state.selectedId = action.payload.id
      state.submitting = false
    })
    builder.addCase(startRun.rejected, (state, action) => {
      state.submitting = false
      state.error = action.error.message
    })
    builder.addCase(sendDecision.pending, (state) => {
      state.submitting = true
      state.error = ''
    })
    builder.addCase(sendDecision.fulfilled, (state, action) => {
      if (state.selectedId === action.payload.id) state.current = action.payload
      state.submitting = false
    })
    builder.addCase(sendDecision.rejected, (state, action) => {
      state.submitting = false
      state.error = action.error.message
    })
  }
})

export const { newNewsletter } = newslettersSlice.actions
export const store = configureStore({
  reducer: { newsletters: newslettersSlice.reducer }
})
