const path = require('path');
const slsw = require('serverless-webpack');
const nodeExternals = require('webpack-node-externals');

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
                test: /^(?!.*\.spec\.ts$).*\.ts$/,
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
    externals: [nodeExternals()],
    devtool: 'source-map'
};