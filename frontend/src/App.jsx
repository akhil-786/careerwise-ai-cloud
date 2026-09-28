import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Onboarding from "./pages/Onboarding";
import Assessment from "./pages/Assessment";
import Recommendation from "./pages/Recommendation";
import Roadmap from "./pages/Roadmap";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/assessment" element={<Assessment />} />
        <Route path="/recommendation" element={<Recommendation />} />
        <Route path="/roadmap" element={<Roadmap />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;