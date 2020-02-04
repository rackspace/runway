const path = require('path');
const slsw = require('serverless-webpack');

// If dependencies can't be properly included in-line, then switch to
// excluding them via webpack-node-externals
// (`npm i -D webpack-node-externals`, require it here, and use nodeExternals() below)
// const nodeExternals = require('webpack-node-externals');

module.exports = {
    mode: 'production',
    entry: slsw.lib.entries,
    resolve: {
        extensions: [
            '.js',
            '.json',
            '.ts'
        ]
    },
    target: 'node',
    module: {
        rules: [
            {
                test: /^(?!.*\.test\.ts$).*\.ts$/,
                loader: 'ts-loader',
                exclude: /node_modules/
            }
        ],
    },
    output: {
        libraryTarget: 'commonjs',
        path: path.join(__dirname, '.webpack'),
        filename: '[name].js',
    },
    // Can externalize dependencies if needed (see comment on webpack-node-externals above):
    // externals: [nodeExternals()],
    // or alternatively the aws sdk can be ommitted from the package without webpack-node-externals:
    // externals: ['aws-sdk'],
    devtool: 'source-map'
};
