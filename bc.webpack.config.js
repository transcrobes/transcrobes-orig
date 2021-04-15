const CopyPlugin = require("copy-webpack-plugin");
const path = require('path');

const webpack = require('webpack');
const TerserPlugin = require('terser-webpack-plugin');

module.exports = {
  optimization: {
    minimize: false,
    minimizer: [new TerserPlugin({
      extractComments: false,
      // extractComments: true,
      terserOptions: {
        output: { ascii_only: true },
      },
    })],
  },
  entry: {
    background: ["regenerator-runtime/runtime.js", './src/assets/bc/js/background.js', ],
    content: ["regenerator-runtime/runtime.js", './src/assets/bc/js/content.js'],
    options: ["regenerator-runtime/runtime.js", './src/assets/bc/js/options.js', ],
  },
  output: {
    filename: '[name]-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './build/bc/'),
  },
  // devtool: 'source-map',
  // devtool: 'inline-source-map',
  // devtool: 'cheap-module-source-map',
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
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
          options: { name: '[name].[ext]', outputPath: '/build/bc/img/', publicPath: '/static/img/' }
        }]
      }
    ]
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: "src/assets/bc/img", to: "img" },
        { from: "node_modules/@webcomponents/webcomponentsjs/bundles/webcomponents-sd-ce.js",
          to: "webcomponents-sd-ce.js" },
        { from: "src/assets/bc/manifest.json", to: "manifest.json" },
        { from: "src/assets/bc/options.html", to: "options.html" },
        { from: "src/data/static/data/css/transcrobes.css", to: "transcrobes.css" },
      ],
    }),
    new webpack.ProvidePlugin({
      process: 'process/browser',
    }),
  ],
};
