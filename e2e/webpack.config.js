const path = require('path');
const nodeExternals = require('webpack-node-externals');

module.exports = {
  mode: 'development',
  entry: './index.ts',
  devtool: 'source-map',
  resolve: {
    extensions: ['.js', '.jsx', '.json', '.ts', '.tsx'],
  },
  output: {
    libraryTarget: 'commonjs',
    path: path.join(__dirname, '.webpack'),
    filename: '[name].js',
  },
  target: 'node',
  module: {
    rules: [
      {
          test: /^(?!.*\.test\.ts$).*\.ts$/,
          loader: 'ts-loader',
          exclude: /node_modules/
      }
    ]
  },
  optimization: {
    minimize: false
  },
  externals: [nodeExternals()]
};
