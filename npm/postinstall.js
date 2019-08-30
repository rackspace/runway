#!/usr/bin/env node
const os = require('os');
const fs = require('fs');
const path = require('path');

const packageJsonPath = `${__dirname}/package.json`;
const packageJsonContent = JSON.parse(fs.readFileSync(packageJsonPath));
const basepath = `${path.resolve(process.cwd(), '../..')}/node_modules`; // goes to the top level node_modules
const moduleDir = `${basepath}/${packageJsonContent.name}/src`;
let osName;

function symLink(target, dest_path) {
  return fs.symlink(target, dest_path, (err, data) => {
    if (err && err.code === 'EEXIST') {
      fs.unlink(dest_path, (err, data) => {
        if (err) {
          console.log(err);
          throw err;
        } else {
          return symLink(target, dest_path);
        }
      });
    } else {
      return err, data;
    }
  });
}

if (os.platform() === 'darwin') {
  osName = 'osx';
} else {
  osName = os.platform();
}

fs.mkdirSync(`${basepath}/.bin`, { recursive: true });

if (os.platform() !== 'win32') {
  // create symlink in bin to the appropriate runway binary
  symLink(`${moduleDir}/${osName}/runway`, `${basepath}/.bin/runway`);
} else {
  // windows does not play nice with a symlink of an exe
  fs.copyFile(`${__dirname}/src/windows/runway.exe`, path.resolve(__dirname, '../.bin/runway.exe'), (err, data) => {
    if (err) throw err;
  });
}

