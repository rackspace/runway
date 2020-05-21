###################
Directory Structure
###################

Example directory structures for a ref:`static site <mod-staticsite>` module.


***********
Angular SPA
***********

.. code-block::

  .
  ├── runway.yml
  └── sample-app
      ├── README.md
      ├── .gitignore
      ├── angular.json
      ├── browserslist
      ├── e2e
      │   ├── protractor.conf.js
      │   ├── src
      │   │   ├── app.e2e-spec.ts
      │   │   └── app.po.ts
      │   └── tsconfig.json
      ├── karma.conf.js
      ├── package-lock.json
      ├── package.json
      ├── src
      │   ├── app
      │   │   ├── app-routing.module.ts
      │   │   ├── app.component.css
      │   │   ├── app.component.html
      │   │   ├── app.component.spec.ts
      │   │   ├── app.component.ts
      │   │   └── app.module.ts
      │   ├── assets
      │   ├── environments
      │   │   ├── environment.prod.ts
      │   │   └── environment.ts
      │   ├── favicon.ico
      │   ├── index.html
      │   ├── main.ts
      │   ├── polyfills.ts
      │   ├── styles.css
      │   └── test.ts
      ├── tsconfig.app.json
      ├── tsconfig.json
      ├── tsconfig.spec.json
      └── tslint.json

*********
React SPA
*********

.. code-block::

  .
  ├── runway.yml
  └── sample-app
      ├── README.md
      ├── package.json
      ├── public
      │   ├── favicon.ico
      │   ├── index.html
      │   ├── logo192.png
      │   ├── logo512.png
      │   ├── manifest.json
      │   └── robots.txt
      └── src
          ├── App.css
          ├── App.js
          ├── App.test.js
          ├── index.css
          ├── index.js
          ├── logo.svg
          ├── serviceWorker.js
          └── setupTests.js
