const path = require('path');

module.exports = {
  entry: {
    readium: ['./src/assets/js/readium.js'],
  },
  output: {
    filename: '[name]-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './src/static'),  // path to our Django static directory
    library: 'readium',
    libraryTarget: 'umd',
  },
};
