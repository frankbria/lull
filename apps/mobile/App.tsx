import { TrackBuilderProvider } from "./src/TrackBuilderContext";
import { TrackBuilderScreen } from "./src/TrackBuilderScreen";

export default function App() {
  return (
    <TrackBuilderProvider>
      <TrackBuilderScreen />
    </TrackBuilderProvider>
  );
}
