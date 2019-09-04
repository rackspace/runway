#!/usr/bin/env node
const os = require('os');
const fs = require('fs');
const path = require('path');
const tar = require('tar');

const packageJsonPath = `${__dirname}/package.json`;
const packageJsonContent = JSON.parse(fs.readFileSync(packageJsonPath));
const basepath = `${path.resolve(process.cwd(), '../..')}/node_modules`; // goes to the top level node_modules
const moduleDir = `${basepath}/${packageJsonContent.name}/src`;
let osName;

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

fs.mkdirSync(`${basepath}/.bin`, { recursive: true });
fs.mkdir(`${moduleDir}/runway`, { recursive: true }, (err, data) => {
  if (err) throw err;

  // unzip the tar for os version to ./src/runway
  tar.x({
    cwd: `${moduleDir}/runway`,
    file: `${moduleDir}/${osName}/runway.tar.gz`,
    gzip: true,
    unlink: true
  }, (err, data) => {
    if (os.platform() !== 'win32') {
      // create symlink in bin to the appropriate runway binary
      symLink(`${moduleDir}/runway/runway-cli`, `${basepath}/.bin/runway`, (err, data) => {
        if (err) throw err;
      });
    } else {
      // symlink does not work for windows so we need to use a bat file
      // this will overwrite the file if it already exists so no fancy error handling needed
      fs.writeFile(`${basepath}/.bin/runway.bat`, `@${moduleDir}/runway/runway-cli.exe %*`, (err, data) => {
        if (err) throw err;
      })
    }
  });
});
