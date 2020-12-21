const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: {
    media: ['./src/assets/js/media.js'],
  },
  output: {
    filename: '[name]-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './src/static'),  // path to our Django static directory
    library: 'media',
    libraryTarget: 'umd',
  },
  plugins: [
    new webpack.ProvidePlugin({
      process: 'process/browser',
    }),
  ]
};
