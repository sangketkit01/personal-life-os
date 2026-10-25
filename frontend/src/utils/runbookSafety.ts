/**
 * Policy: Any command that is NOT explicitly identified as read-only inspection
 * MUST require confirmation before execution.
 */

export function isReadOnlyCommand(rawCmd: string): boolean {
  if (!rawCmd || !rawCmd.trim()) return false

  // 1. Any command substitution $(...) or `...` can execute arbitrary commands
  if (/\$\(|`/.test(rawCmd)) return false

  // 2. Any redirection (<, >, >>, etc.) is a write or input diversion
  if (/[<>]/.test(rawCmd)) return false

  // 3. Execution wrappers / privilege escalation / scripting interpreters
  if (/\b(sudo|su|eval|exec|xargs|tee|env|sh|bash|zsh|python|perl|ruby|node)\b/i.test(rawCmd)) {
    return false
  }

  // Split by pipeline (|) and command separators (&&, ||, ;, newline)
  const segments = rawCmd
    .split(/[\r\n;&|]+/)
    .map(s => s.trim())
    .filter(Boolean)

  if (segments.length === 0) return false

  // Every segment must match a strict read-only inspection rule
  return segments.every(isReadOnlySegment)
}

function isReadOnlySegment(seg: string): boolean {
  const parts = seg.split(/\s+/).filter(Boolean)
  if (parts.length === 0) return false

  const cmd = parts[0].toLowerCase()
  const args = parts.slice(1)
  const fullArgs = args.join(' ').toLowerCase()

  // Common file and text inspection tools
  if (['cat', 'head', 'tail', 'more', 'less'].includes(cmd)) {
    return true
  }

  if (['grep', 'egrep', 'fgrep'].includes(cmd)) {
    return true
  }

  if (['ls', 'dir', 'pwd', 'whoami', 'id', 'uname', 'uptime', 'free', 'df', 'du'].includes(cmd)) {
    return true
  }

  // date: read-only when querying or formatting, but requires confirmation when setting time
  if (cmd === 'date') {
    if (/(?:^|\s)(?:-s\b|-s\s|--set)/i.test(fullArgs)) {
      return false
    }
    const allowedDateFlags = new Set([
      '-u', '--utc', '--universal',
      '-r', '--reference',
      '-d', '--date',
      '-R', '--rfc-email', '--rfc-2822', '--rfc-3339',
      '-I', '--iso-8601',
      '--help', '--version'
    ])
    for (let i = 0; i < args.length; i++) {
      const a = args[i]
      if (a.startsWith('+')) continue
      if (allowedDateFlags.has(a.toLowerCase())) continue
      if (/^--date=/i.test(a) || /^--reference=/i.test(a) || /^--rfc-3339=/i.test(a) || /^-I/i.test(a) || /^--iso-8601=/i.test(a)) {
        continue
      }
      const prev = args[i - 1]?.toLowerCase()
      if (prev && ['-d', '--date', '-r', '--reference'].includes(prev)) {
        continue
      }
      // Any non-whitelisted flag or positional time-setting argument (e.g. date 01010000)
      return false
    }
    return true
  }

  // hostname: read-only when querying, but requires confirmation when setting hostname
  if (cmd === 'hostname') {
    if (args.length === 0) return true
    // Explicitly reject mutating flags: -F (case-sensitive) / --file, and -b / --boot
    if (/(?:^|\s)-F(?:\s|$)/.test(args.join(' ')) || /(?:^|\s)(?:--file\b|--file=|-b(?:\s|$)|--boot\b)/i.test(fullArgs)) {
      return false
    }
    const allowedHostnameFlags = new Set([
      '-a', '--alias',
      '-d', '--domain',
      '-f', '--fqdn', '--long',
      '-A', '--all-fqdns',
      '-i', '--ip-address',
      '-I', '--all-ip-addresses',
      '-s', '--short',
      '-y', '--yp', '--nis',
      '-v', '--verbose',
      '-V', '--version',
      '--help'
    ])
    for (const a of args) {
      if (!allowedHostnameFlags.has(a) && !allowedHostnameFlags.has(a.toLowerCase())) {
        return false
      }
    }
    return true
  }

  if (['top', 'htop', 'ps', 'pstree', 'pgrep', 'netstat', 'ss', 'arp'].includes(cmd)) {
    return true
  }

  if (['ping', 'traceroute', 'tracepath', 'dig', 'nslookup', 'host'].includes(cmd)) {
    return true
  }

  // curl: only header / inspection requests
  if (cmd === 'curl') {
    return args.includes('-I') || args.includes('--head')
  }

  // git: only inspection commands without mutating options
  if (cmd === 'git') {
    if (args.length === 0) return false
    const gitSub = args[0].toLowerCase()

    if (['status', 'log', 'diff', 'show'].includes(gitSub)) {
      return true
    }

    if (gitSub === 'branch') {
      // Must NOT contain -d, -D, -m, -M, -c, -C, --delete, --move, --copy
      if (/(?:^|\s)(?:-[dDmMcC]|--delete|--move|--copy)(?:\s|$|=)/.test(fullArgs)) {
        return false
      }
      // If there are positional branch names without listing flags, it creates a branch
      const nonFlags = args.slice(1).filter(a => !a.startsWith('-'))
      return nonFlags.length === 0
    }

    if (gitSub === 'tag') {
      // Only listing tags
      if (/(?:^|\s)(?:-[das]|--delete)(?:\s|$|=)/.test(fullArgs)) {
        return false
      }
      const nonFlags = args.slice(1).filter(a => !a.startsWith('-'))
      return nonFlags.length === 0 || args.includes('-l') || args.includes('--list')
    }

    return false
  }

  // ip: only show/list without set, add, del, flush, etc.
  if (cmd === 'ip') {
    if (/\b(set|add|del|delete|change|replace|flush)\b/i.test(fullArgs)) {
      return false
    }
    const ipSub = args[0]?.toLowerCase()
    return ['a', 'addr', 'address', 'l', 'link', 'r', 'route', 'neigh', 'neighbor', 'netns'].includes(ipSub)
  }

  // docker: only ps, logs, inspect, top, stats
  if (cmd === 'docker') {
    if (args.length === 0) return false
    const dockerSub = args[0].toLowerCase()
    if (dockerSub === 'compose') {
      const composeSub = args[1]?.toLowerCase()
      return ['ps', 'logs', 'top', 'config'].includes(composeSub)
    }
    return ['ps', 'logs', 'inspect', 'top', 'stats'].includes(dockerSub)
  }

  // systemctl: only status and inspection queries
  if (cmd === 'systemctl') {
    if (args.length === 0) return false
    const sub = args[0].toLowerCase()
    return ['status', 'is-active', 'is-enabled', 'is-failed', 'list-units', 'list-unit-files'].includes(sub)
  }

  if (cmd === 'service') {
    return args[args.length - 1]?.toLowerCase() === 'status'
  }

  // journalctl: strictly rejecting destructive options like --vacuum, --rotate, --flush
  if (cmd === 'journalctl') {
    if (/(?:^|\s)--(?:vacuum-time|vacuum-size|vacuum-files|vacuum|rotate|flush|relinquish-var)(?:=|\s|$)/i.test(fullArgs)) {
      return false
    }
    return true
  }

  // echo / printf: plain terminal output without variables or flags that could be abused
  if (['echo', 'printf'].includes(cmd)) {
    return true
  }

  return false
}

export function requiresConfirmation(cmd: string): boolean {
  return !isReadOnlyCommand(cmd)
}
