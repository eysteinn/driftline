import { create } from 'zustand'
import type { Mission, CreateMissionRequest, MissionResult } from '../types'
import { apiClient } from '../services/api'

interface MissionState {
  missions: Mission[]
  currentMission: Mission | null
  currentResult: MissionResult | null
  isLoading: boolean
  error: string | null
  
  fetchMissions: () => Promise<void>
  fetchMission: (id: string) => Promise<void>
  createMission: (data: CreateMissionRequest) => Promise<Mission>
  deleteMission: (id: string) => Promise<void>
  fetchMissionResults: (id: string) => Promise<void>
  clearError: () => void
  clearCurrentMission: () => void
}

export const useMissionStore = create<MissionState>((set) => ({
  missions: [],
  currentMission: null,
  currentResult: null,
  isLoading: false,
  error: null,

  fetchMissions: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.getMissions()
      set({ missions: response.data || [], isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to fetch missions',
        isLoading: false,
      })
    }
  },

  fetchMission: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const mission = await apiClient.getMission(id)
      set({ currentMission: mission, isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to fetch mission',
        isLoading: false,
      })
    }
  },

  createMission: async (data: CreateMissionRequest) => {
    set({ isLoading: true, error: null })
    try {
      const mission = await apiClient.createMission(data)
      set((state) => ({
        missions: [mission, ...state.missions],
        currentMission: mission,
        isLoading: false,
      }))
      return mission
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to create mission',
        isLoading: false,
      })
      throw error
    }
  },

  deleteMission: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.deleteMission(id)
      set((state) => ({
        missions: state.missions.filter((m) => m.id !== id),
        currentMission: state.currentMission?.id === id ? null : state.currentMission,
        isLoading: false,
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to delete mission',
        isLoading: false,
      })
      throw error
    }
  },

  fetchMissionResults: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const result = await apiClient.getMissionResults(id)
      set({ currentResult: result, isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to fetch results',
        isLoading: false,
      })
    }
  },

  clearError: () => set({ error: null }),
  clearCurrentMission: () => set({ currentMission: null, currentResult: null }),
}))
