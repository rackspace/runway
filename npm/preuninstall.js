#!/usr/bin/env node
const os = require('os');
const fs = require('fs');
const path = require('path');

const basepath = `${path.resolve(process.cwd(), '../..')}/node_modules`; // goes to the top level node_modules

if (os.platform() === 'win32') {
  if (process.env.npm_config_global) {
    binPath = path.resolve(process.env.APPDATA, './npm/runway.bat');
  } else {
    binPath = `${basepath}/.bin/runway.bat`;
  }
} else {
  if (process.env.npm_config_global) {
    binPath = `${process.env.NVM_BIN || '/usr/local/bin'}/runway`;
  } else {
    binPath = `${basepath}/.bin/runway`;
  }
}

// remove symlink/exe from bin created by postinstall script
fs.unlink(binPath, (err, data) => {
  if (err) {
    // ignore file/dir missing
    if (err.code !== 'ENOENT') {
      throw err;
    }
  }
});
