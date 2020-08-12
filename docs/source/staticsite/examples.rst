.. _staticsite-examples:

########
Examples
########

Example uses of the :ref:`static site <mod-staticsite>` module


***********
Angular SPA
***********

To view an example deployment of an `Angular <https://angular.io/>`__ single page application, run ``runway gen-sample static-angular`` in any directory.
This will create a new ``static-angular/`` directory in your current working directory containing a ``runway.yml`` and a ``sample-app`` module that can be deployed.

Extra Files in Angular
=========================
By default, angular uses ``environment/environment.ts`` as its way to pass environment specific configurations into
your application. The downside to this is that you need to build your application for each environment and lose ability
to build once and deploy everywhere.

The static site ``extra_files`` option solves this problem by moving environment configuration out of angular and
into runway. A small change to the way the application references environment config will need to be made.

#. Wrap configuration access into a service that can be injected into your components.

#. In the new config service, make an http request to load the config. Since ``extra_files`` uploads the files to
   the static site bucket, this request should be relative to your application.

#. Cache the config and use normal observable patterns to provide access.

.. rubric:: app.config.ts
.. code-block:: typescript

  export interface Config {
    endpoint: string;
  }

  @Injectable({
    providedIn: 'root'
  })
  export class AppConfig {
    constructor(private http: HttpClient) {}

    getConfig(): Observable<Config> {
      return this.http.get<Config>('assets/config.json');
    }
  }

.. rubric:: app.component.ts
.. code-block:: typescript

  export class AppComponent implements OnInit {
    title = 'Angular App';

    constructor(private config: AppConfig) {}

    ngOnInit() {
      this.config.getConfig().subscribe((config) => {
        this.title = config.endpoint;
      });
    }
  }

.. rubric:: runway.yaml
.. code-block:: yaml

  ---
  variables:
    website:
      api_endpoint:
        dev: https://api.dev.example.com
        test: https://api.test.example.com
  deployments:
    - name: WebApp
      modules:
        - path: .
          type: static
          environments:
            dev: true
            test: true
          options:
            build_steps:
              - npm ci
              - npm run build
            build_output: dist/web
            extra_files:
              - name: assets/config.json
                content:
                  endpoint: ${var website.api_endpoint.${env DEPLOY_ENVIRONMENT}}
          parameters:
            namespace: my-app-namespace
            staticsite_cf_disable: true
      regions:
        - us-east-1

Angular Development Workflow
============================
While developing an Angular application, a local live environment is typically used and Runway is not. This means that
``assets/config.json`` does not exist and your application would likely fail. Take the following steps to get your
development environment running.

#. Create a stub ``src/assets/config.json`` that defines all the configuration attributes. The values can be empty
   strings.

#. Create a 'dev' config file: ``src/assets/config-dev.json``. Populate the configuration values with appropriate
   values for your local dev environment.

#. Edit ``angular.json``

   * Add a ``fileReplacements`` option to ``projects.<app>.architect.build.options``.

     .. code-block:: json

        {
          "fileReplacements": [{
            "replace": "src/assets/config.json",
            "with": "src/assets/config-dev.json"
          }]
        }

#. Run ``npx ng serve``

.. note::

   It would be a better practice to define a new 'local' configuration target instead of adding ``fileReplacements``
   to the default configuration target.

   **"build" Configuration**

   .. code-block:: json

      {
        "configurations": {
          "local": {
            "fileReplacements": [{
              "replace": "src/assets/config.json",
              "with": "src/assets/config-local.json"
            }]
          }
        }
      }

   **"serve" Configuration**

   .. code-block:: json

      {
        "configurations": {
          "local": {
            "browserTarget": "<app>:build:local"
          }
        }
      }

   .. code-block:: bash

      $ npx ng serve --configuration=local

*********
React SPA
*********

To view an example deployment of a `React <https://reactjs.org/>`__ single page application, run ``runway gen-sample static-react`` in any directory.
This will create a new ``static-react/`` directory in your current working directory containing a ``runway.yml`` and a ``sample-app`` module that can be deployed.

Extra Files in React
====================
React by itself is not concerned with different environments or how a developer initializes the application with
different backends. This is more of a concern with other layers of your application stack, e.g. Redux. However, the
concept is similar to the Angular examples.

**Plain React**

.. code-block:: jsx

    // Use your favorite http client
    import axios from 'axios';

    // Make a request to load the config
    axios.get('config.json').then(resp => {
      return resp.data.endpoint;
    })
    .then(endpoint => {
      // Render the react component
      ReactDOM.render(<App message={endpoint} />, document.getElementById('root'));
    });

**React Redux**

Initialize the redux store with an initial config

.. code-block:: jsx

    axios.get('config.json').then(resp => {
      return resp.data;
    })
    .then(config => {
      // Create a redux store
      return store(config);
    })
    .then(store => {
      ReactDOM.render(
        <Provider store={store}>
          <App/>
        </Provider>,
        document.getElementById('root')
      );
    });

**Runway Config**

.. code-block:: yaml

  ---
  ignore_git_branch: true
  variables:
    website:
      api_endpoint:
        dev: https://api.dev.example.com
        test: https://api.test.example.com
  deployments:
    - name: WebApp
      modules:
        - path: .
          type: static
          environments:
            dev: true
            test: true
          options:
            build_output: build
            build_steps:
              - npm ci
              - npm run build
            extra_files:
              - name: config.json
                content:
                  endpoint: ${var website.api_endpoint.${env DEPLOY_ENVIRONMENT}}
          parameters:
            namespace: my-app-namespace
            staticsite_cf_disable: true
      regions:
        - us-west-2


React Development Workflow
==========================
React doesn't have an equivalent feature as Angular's fileReplacements so this solution isn't as flexible.

#. Create the file ``public/config.json``.

   Add content that matches the structure defined in ``extra_files`` and populate the values needed for local
   development.

   **Example**

   .. code-block:: json

      {
        "endpoint": "https://api.dev.example.com"
      }

#. *(Optional)* Add ``public/config.json`` to ``.gitignore``

    .. note::

      If you don't want to add ``public/config.json`` to ``.gitignore``, you should configure Runways source hashing
      to exclude it.

      .. code-block:: yaml

          source_hashing:
            enabled: true
            directories:
              - path: ./
                exclusions:
                  - public/config.json

#. Run ``npm run start``
