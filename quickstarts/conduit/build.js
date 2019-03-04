const fs = require("fs");
const util = require("util");
const { exec } = require("child_process");
const execAsync = util.promisify(exec);

(async () => {
  let env = "dev";
  try {
    dev = execAsync("pipenv run runway whichenv");
  } catch (err) {
    console.error(err);
    return;
  }

  if (env === "prod") {
    try {
      await execAsync(`npx ng build --prod --base-href .`);
    } catch (error) {
      console.error(error);
      return;
    }
  } else {
    try {
      await execAsync(`npx ng build --base-href .`);
    } catch (error) {
      console.error(error);
      return;
    }
    fs.copyFileSync("./CNAME", "./dist/CNAME");
  }
})();
