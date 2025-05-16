const webpack = require('webpack');
const path = require('path');

module.exports = {
  webpack: {
    configure: {
      resolve: {
        fallback: {
          crypto: require.resolve('crypto-browserify'),
          stream: require.resolve('stream-browserify'),
          buffer: require.resolve('buffer/'),
          util: require.resolve('util/'),
          process: require.resolve('process/browser'),
          zlib: require.resolve('browserify-zlib'),
        },
      },
      plugins: [
        new webpack.ProvidePlugin({
          process: 'process/browser.js',
          Buffer: ['buffer', 'Buffer'],
        }),
      ],
    },
  },
};