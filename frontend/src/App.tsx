import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import XhsTool from "./pages/XhsTool";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/xhs" element={<XhsTool />} />
    </Routes>
  );
}
