#!/usr/bin/env node
const os = require('os');
const fs = require('fs');
const path = require('path');
const tar = require('tar');

// e.g. '../..' for 'runway'; '../../..' for `@onica/runway', etc
let pathTraversal = '..'
for (var i = 0; i < process.env.npm_package_name.split("/").length; i++) {
    pathTraversal += '/..'
}

const basepath = `${path.resolve(process.cwd(), pathTraversal)}/node_modules`; // goes to the top level node_modules
const moduleDir = `${basepath}/${process.env.npm_package_name}/src`;
let osName;
let binPath;

function symLink(target, dest_path, callback) {
  return fs.symlink(target, dest_path, 'file', (err, data) => {
    // error is thrown if the file already exists
    if (err && err.code === 'EEXIST') {
      fs.unlink(dest_path, (err, data) => {
        if (err) {
          console.log(err);
          throw err;
        } else {
          return symLink(target, dest_path, callback);
        }
      });
    } else {
      return callback(err, data);
    }
  });
}

// translate os name used during binary build
switch (os.platform()) {
  case 'darwin':
    osName = 'osx';
    break;
  case 'win32':
    osName = 'windows';
    break;
  default:
    osName = os.platform();
}

fs.mkdir(`${moduleDir}/runway`, { recursive: true }, (err, data) => {
  if (err) throw err;

  // unzip the tar for os version to ./src/runway
  tar.x({
    cwd: `${moduleDir}/runway`,
    file: `${moduleDir}/${osName}/runway.tar.gz`,
    gzip: true,
    unlink: true
  }, (err, data) => {
    if (err) throw err;

    if (os.platform() !== 'win32') {
      // determine correct bin path to use based on global/local install
      if (process.env.npm_config_global) {
        binPath = `${process.env.NVM_BIN || '/usr/local/bin'}/runway`;
      } else {
        try {
          fs.mkdirSync(`${basepath}/.bin`, { recursive: true });
        } catch (err) {
          // shouldn't need to catch an EEXIST error with the recursive option
          // set on mkdirSync, but it still can occur (e.g. on older
          // versions of nodejs without the recursive option)
          // https://github.com/nodejs/node/issues/27293
          if (err && err.code !== 'EEXIST') {
            throw err;
          }
        }
        binPath = `${basepath}/.bin/runway`;
      }
      // create symlink in bin to the appropriate runway binary
      symLink(`${moduleDir}/runway/runway-cli`, binPath, (err, data) => {
        if (err) {
          if (err.code === 'EACCES') {
            console.log('User does not have sufficient privileges to install. Please try again with sudo.')
          }
          throw err;
        }
      });
    } else {
      // determine correct bin path to use based on global/local install
      if (process.env.npm_config_global) {
        binPath = path.resolve(process.env.APPDATA, './npm/runway.bat');
      } else {
        fs.mkdirSync(`${basepath}/.bin`, { recursive: true });
        binPath = `${basepath}/.bin/runway.bat`;
      }
      // symlink does not work for windows so we need to use a bat file
      // this will overwrite the file if it already exists so no fancy error handling needed
      fs.writeFile(binPath, `@"${moduleDir}/runway/runway-cli.exe" %*`, (err, data) => {
        if (err) throw err;
      })
    }
  });
});
