const path = require('path');

module.exports = {
  entry: {
    survey: ['./src/assets/survey.app.jsx' ],
    notrobes: ['./src/assets/notrobes.app.jsx']
  },
  output: {
    filename: '[name]-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './src/static'),  // path to our Django static directory
  },
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
          options: { name: '[name].[ext]', outputPath: '/img/', publicPath: '/static/img/' }
        }]
      }
    ]
  }
};
