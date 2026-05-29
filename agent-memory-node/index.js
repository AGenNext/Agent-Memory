'use strict'

const { existsSync, readFileSync } = require('fs')
const { join } = require('path')

const { platform, arch } = process

let nativeBinding = null
let loadError = null

function isMusl() {
  if (!existsSync('/usr/bin/ldd')) return true
  return readFileSync('/usr/bin/ldd', 'utf8').includes('musl')
}

switch (platform) {
  case 'win32':
    switch (arch) {
      case 'x64':
        localFileExisted = existsSync(join(__dirname, 'agent-memory.win32-x64-msvc.node'))
        try {
          nativeBinding = localFileExisted
            ? require('./agent-memory.win32-x64-msvc.node')
            : require('@agentnxxt/agent-memory-win32-x64-msvc')
        } catch (e) { loadError = e }
        break
      default:
        throw new Error(`Unsupported Windows arch: ${arch}`)
    }
    break
  case 'darwin':
    switch (arch) {
      case 'arm64':
        localFileExisted = existsSync(join(__dirname, 'agent-memory.darwin-arm64.node'))
        try {
          nativeBinding = localFileExisted
            ? require('./agent-memory.darwin-arm64.node')
            : require('@agentnxxt/agent-memory-darwin-arm64')
        } catch (e) { loadError = e }
        break
      case 'x64':
        localFileExisted = existsSync(join(__dirname, 'agent-memory.darwin-x64.node'))
        try {
          nativeBinding = localFileExisted
            ? require('./agent-memory.darwin-x64.node')
            : require('@agentnxxt/agent-memory-darwin-x64')
        } catch (e) { loadError = e }
        break
      default:
        throw new Error(`Unsupported macOS arch: ${arch}`)
    }
    break
  case 'linux':
    switch (arch) {
      case 'x64':
        if (isMusl()) {
          localFileExisted = existsSync(join(__dirname, 'agent-memory.linux-x64-musl.node'))
          try {
            nativeBinding = localFileExisted
              ? require('./agent-memory.linux-x64-musl.node')
              : require('@agentnxxt/agent-memory-linux-x64-musl')
          } catch (e) { loadError = e }
        } else {
          localFileExisted = existsSync(join(__dirname, 'agent-memory.linux-x64-gnu.node'))
          try {
            nativeBinding = localFileExisted
              ? require('./agent-memory.linux-x64-gnu.node')
              : require('@agentnxxt/agent-memory-linux-x64-gnu')
          } catch (e) { loadError = e }
        }
        break
      case 'arm64':
        if (isMusl()) {
          localFileExisted = existsSync(join(__dirname, 'agent-memory.linux-arm64-musl.node'))
          try {
            nativeBinding = localFileExisted
              ? require('./agent-memory.linux-arm64-musl.node')
              : require('@agentnxxt/agent-memory-linux-arm64-musl')
          } catch (e) { loadError = e }
        } else {
          localFileExisted = existsSync(join(__dirname, 'agent-memory.linux-arm64-gnu.node'))
          try {
            nativeBinding = localFileExisted
              ? require('./agent-memory.linux-arm64-gnu.node')
              : require('@agentnxxt/agent-memory-linux-arm64-gnu')
          } catch (e) { loadError = e }
        }
        break
      default:
        throw new Error(`Unsupported Linux arch: ${arch}`)
    }
    break
  default:
    throw new Error(`Unsupported platform: ${platform}`)
}

if (!nativeBinding) {
  if (loadError) {
    throw loadError
  }
  throw new Error('Failed to load native binding for agent-memory')
}

module.exports = nativeBinding
