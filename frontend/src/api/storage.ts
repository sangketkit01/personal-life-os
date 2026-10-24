import apiClient from './client'

export interface GoogleDriveStatus {
  is_connected: boolean
  google_email: string
  root_folder_id: string
  subfolder_ids: Record<string, string>
  created_at?: string
  updated_at?: string
}

export interface InitiateUploadResponse {
  upload_url: string
  file_name: string
  file_type: string
  file_size: number
  parent_folder_id: string
}

export interface DriveFileItem {
  id: string
  drive_file_id: string
  file_name: string
  file_type: string
  file_size: number
  web_view_link: string
  web_content_link: string
  thumbnail_link: string
  domain: string
  target_id: string
  uploaded_at: string
}

export async function getGoogleAuthUrl(): Promise<{ auth_url: string }> {
  const res = await apiClient.get('/storage/auth/url/')
  return res.data
}

export async function googleAuthCallback(
  code: string,
  state?: string
): Promise<{ message: string; status: GoogleDriveStatus }> {
  const payload: Record<string, string> = { code }
  if (state) payload.state = state
  const res = await apiClient.post('/storage/auth/callback/', payload)
  return res.data
}

export async function getGoogleDriveStatus(): Promise<GoogleDriveStatus> {
  const res = await apiClient.get('/storage/status/')
  return res.data
}

export async function initiateResumableUpload(payload: {
  domain: string
  file_name: string
  file_type: string
  file_size: number
}): Promise<InitiateUploadResponse> {
  const res = await apiClient.post('/storage/initiate-upload/', payload)
  return res.data
}

export async function uploadBytesDirectToGoogle(
  uploadUrl: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ id: string; name: string; webViewLink?: string; webContentLink?: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', uploadUrl, true)
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          const percent = Math.round((evt.loaded / evt.total) * 100)
          onProgress(percent)
        }
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText)
          resolve(data)
        } catch {
          resolve({ id: '', name: file.name })
        }
      } else {
        reject(new Error(`Direct Google Drive upload failed with status ${xhr.status}: ${xhr.statusText}`))
      }
    }

    xhr.onerror = () => {
      reject(new Error('Network error occurred during direct Google Drive upload.'))
    }

    xhr.send(file)
  })
}

export async function completeResumableUpload(payload: {
  drive_file_id: string
  domain: string
  target_id?: string
  file_name: string
  file_type?: string
  file_size?: number
}): Promise<DriveFileItem> {
  const res = await apiClient.post('/storage/complete-upload/', payload)
  return res.data
}

export async function disconnectGoogleDrive(): Promise<{ message: string }> {
  const res = await apiClient.post('/storage/disconnect/')
  return res.data
}

export async function getDriveFiles(domain?: string, targetId?: string): Promise<DriveFileItem[]> {
  const params: Record<string, string> = {}
  if (domain) params.domain = domain
  if (targetId) params.target_id = targetId
  const res = await apiClient.get('/storage/files/', { params })
  return res.data
}

export async function deleteDriveFile(id: string): Promise<void> {
  await apiClient.delete(`/storage/files/${id}/`)
}

/** Idempotent DELETE of a Drive file by its Google Drive file id. */
export async function deleteFileByDriveId(driveFileId: string): Promise<void> {
  await apiClient.delete(`/storage/files/by-drive-id/${driveFileId}/`)
}
