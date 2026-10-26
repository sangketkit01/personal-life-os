export interface SshHostKeyErrorInfo {
  isHostKeyError: boolean
  isMismatch: boolean
  hostname: string
  remoteFingerprint: string
  trustedFingerprint: string
}

/**
 * Parse SshConnectionError message to extract host key verification status and fingerprints.
 */
export function parseSshHostKeyError(message?: string | null): SshHostKeyErrorInfo {
  if (!message || typeof message !== 'string') {
    return {
      isHostKeyError: false,
      isMismatch: false,
      hostname: '',
      remoteFingerprint: '',
      trustedFingerprint: ''
    }
  }

  // 1. Check for Host Key Identification Changed (MITM / Mismatch)
  // Example: WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED FOR 'myserver'! Remote host key fingerprint is SHA256:..., but trusted fingerprint is SHA256:...
  const mismatchMatch = message.match(
    /REMOTE HOST IDENTIFICATION HAS CHANGED FOR ['"]?([^'"]+)['"]?!.*(?:fingerprint is|fingerprint:?)\s*([A-Za-z0-9+/=:]+).*?(?:trusted fingerprint is|trusted:?)\s*([A-Za-z0-9+/=:]+)/is
  )
  if (mismatchMatch) {
    return {
      isHostKeyError: true,
      isMismatch: true,
      hostname: mismatchMatch[1].trim(),
      remoteFingerprint: mismatchMatch[2].trim(),
      trustedFingerprint: mismatchMatch[3].trim()
    }
  }

  // 2. Check for Unverified / First-time Host Key
  // Example: SSH host key for 'myserver' is not verified. Server fingerprint: SHA256:...
  const unverifiedMatch = message.match(
    /SSH host key for ['"]?([^'"]+)['"]? is not verified\.\s*(?:Server fingerprint:?)\s*([A-Za-z0-9+/=:]+)/is
  )
  if (unverifiedMatch) {
    return {
      isHostKeyError: true,
      isMismatch: false,
      hostname: unverifiedMatch[1].trim(),
      remoteFingerprint: unverifiedMatch[2].trim(),
      trustedFingerprint: ''
    }
  }

  // Generic fallback if text contains "fingerprint" and "not verified"
  if (message.toLowerCase().includes('not verified') && message.includes('SHA256:')) {
    const fpMatch = message.match(/SHA256:[A-Za-z0-9+/=]+/i)
    return {
      isHostKeyError: true,
      isMismatch: false,
      hostname: '',
      remoteFingerprint: fpMatch ? fpMatch[0] : '',
      trustedFingerprint: ''
    }
  }

  return {
    isHostKeyError: false,
    isMismatch: false,
    hostname: '',
    remoteFingerprint: '',
    trustedFingerprint: ''
  }
}
