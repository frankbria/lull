// AsyncStorage is a native module; in node tests use its official in-memory mock so the
// persistence round-trip runs for real against an in-memory store.
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);
