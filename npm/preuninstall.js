#!/usr/bin/env node
const os = require('os');
const fs = require('fs');
const path = require('path');

var runwayExe = 'runway';

if (os.platform() === 'win32') {
  runwayExe = 'runway.exe';
}

// remove symlink/exe from bin created by postinstall script
fs.unlink(path.resolve(__dirname, `../bin/${runwayExe}`), (err, data) => {
  if (err) {
    // ignore file/dir missing
    if (err.code !== 'ENOENT') {
      throw err;
    }
  }
});
