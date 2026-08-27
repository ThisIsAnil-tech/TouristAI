require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    localhost: {
      url: "http://0.0.0.0:8545",
      chainId: 1337,
    },
    hardhat: {
      chainId: 1337,
      mining: {
        auto: true,
        interval: 0,
      },
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};
