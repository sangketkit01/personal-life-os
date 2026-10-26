import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getGoogleDriveStatus,
  getGoogleAuthUrl,
  googleAuthCallback,
  initiateResumableUpload,
  uploadBytesDirectToGoogle,
  completeResumableUpload,
  disconnectGoogleDrive,
  deleteFileByDriveId,
  getFileByDriveId,
  type GoogleDriveStatus,
  type DriveFileItem
} from '../api/storage'
import { useToastStore } from './toast'

export const useStorageStore = defineStore('storage', () => {
  const toast = useToastStore()
  const status = ref<GoogleDriveStatus | null>(null)
  const isLoading = ref(false)
  const isConnecting = ref(false)
  const uploadProgress = ref<number | null>(null)

  const isConnected = computed(() => !!status.value?.is_connected)
  const googleEmail = computed(() => status.value?.google_email || '')
  const rootFolderId = computed(() => status.value?.root_folder_id || '')

  async function fetchStatus() {
    isLoading.value = true
    try {
      status.value = await getGoogleDriveStatus()
    } catch {
      status.value = null
    } finally {
      isLoading.value = false
    }
  }

  async function startConnect() {
    isConnecting.value = true
    try {
      const { auth_url } = await getGoogleAuthUrl()
      if (auth_url) {
        window.location.href = auth_url
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to start Google authorization')
    } finally {
      isConnecting.value = false
    }
  }

  async function handleCallback(code: string, state?: string) {
    isLoading.value = true
    try {
      const res = await googleAuthCallback(code, state)
      status.value = res.status
      toast.success('Google Drive connected successfully!')
      return true
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Google Drive authorization failed.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function disconnect() {
    isLoading.value = true
    try {
      await disconnectGoogleDrive()
      status.value = {
        is_connected: false,
        google_email: '',
        root_folder_id: '',
        subfolder_ids: {}
      }
      toast.success('Google Drive disconnected')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to disconnect Google Drive')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * High-level Zero-Disk upload:
   * 1. Confirms Google Drive is linked.
   * 2. Requests Google Resumable Upload URI from backend.
   * 3. Streams file bytes directly into Google Drive (bypassing server disk 100%).
   * 4. Registers metadata with backend.
   */
  async function uploadDirect(
    file: File,
    domain: 'ledger' | 'finance' | 'portfolio' | 'workspace' | 'note' | 'general' = 'general',
    targetId?: string,
    onProgress?: (pct: number) => void
  ): Promise<DriveFileItem> {
    if (!status.value) {
      await fetchStatus()
    }
    if (!isConnected.value) {
      throw new Error('Google Drive connection is required before storing attachments.')
    }

    uploadProgress.value = 0

    try {
      // Step 1: Initiate session with Google Drive through backend
      const session = await initiateResumableUpload({
        domain,
        file_name: file.name,
        file_type: file.type || 'application/octet-stream',
        file_size: file.size
      })

      // Step 2: Stream binary bytes directly to Google Drive
      const gdriveResult = await uploadBytesDirectToGoogle(session.upload_url, file, (pct) => {
        uploadProgress.value = pct
        if (onProgress) onProgress(pct)
      })

      // Step 3: Register metadata in backend with retry & orphan compensation
      let savedFile: DriveFileItem | null = null
      let registerError: any = null
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          savedFile = await completeResumableUpload({
            drive_file_id: gdriveResult.id,
            domain,
            target_id: targetId,
            file_name: file.name,
            file_type: file.type || 'application/octet-stream',
            file_size: file.size
          })
          break
        } catch (err: any) {
          registerError = err
          if (attempt < 2) {
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)))
          }
        }
      }

      if (!savedFile) {
        // Double-check if the file was actually registered on the backend (e.g. response dropped)
        const existingFile = await getFileByDriveId(gdriveResult.id)
        if (existingFile && existingFile.id) {
          uploadProgress.value = null
          return existingFile
        }

        // Step 3 failed after retries and file is not registered: compensate to prevent orphan file on Google Drive
        try {
          await deleteFileByDriveId(gdriveResult.id)
        } catch (cleanupErr) {
          console.warn('Failed to clean up orphaned Drive file:', cleanupErr)
        }
        throw new Error(
          registerError?.response?.data?.error ||
          registerError?.message ||
          'Upload to Google Drive completed, but backend registration failed. The upload was safely rolled back.'
        )
      }

      uploadProgress.value = null
      return savedFile
    } catch (err: any) {
      uploadProgress.value = null
      throw err
    }
  }

  return {
    status,
    isLoading,
    isConnecting,
    isConnected,
    googleEmail,
    rootFolderId,
    uploadProgress,
    fetchStatus,
    startConnect,
    handleCallback,
    disconnect,
    uploadDirect,
    deleteFileByDriveId
  }
})
