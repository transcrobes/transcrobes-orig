const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: {
    app: ['./src/assets/js/app.js'],
    sw: ['./src/assets/js/sw.js'],
    notrobes: ["regenerator-runtime/runtime.js", './src/assets/react-apps/notrobes.app.jsx'],
    srsrobes: ["regenerator-runtime/runtime.js", './src/assets/react-apps/srsrobes.app.jsx'],
    listrobes: ["regenerator-runtime/runtime.js", './src/assets/react-apps/listrobes.app.jsx'],
    survey: ["regenerator-runtime/runtime.js", './src/assets/react-apps/survey.app.jsx'],
  },
  output: {
    filename: '[name]-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './src/static'),  // path to our Django static directory
  },
  module: {
    rules: [
      {
        test: /\.(mjs|js|jsx)$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: {
          presets: ["@babel/preset-env", "@babel/preset-react"],
          plugins: ["@babel/plugin-proposal-class-properties"]
        }
      },
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(png|jp?g|svg|gif)$/,
        use: [{
          loader: "file-loader",
          options: { name: '[name].[ext]', outputPath: '/img/', publicPath: '/static/img/' }
        }]
      }
    ]
  },
  plugins: [
    new webpack.ProvidePlugin({
      process: 'process/browser',
    }),
  ]
};
