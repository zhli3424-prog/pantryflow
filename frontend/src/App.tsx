import { createBrowserRouter, RouterProvider } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import HistoryPage from "./pages/HistoryPage";
import HomePage from "./pages/HomePage";
import IngredientsPage from "./pages/IngredientsPage";
import RecipeDetailPage from "./pages/RecipeDetailPage";
import RecommendationsPage from "./pages/RecommendationsPage";

const router = createBrowserRouter([{
  path: "/",
  element: <AppLayout />,
  children: [
    { index: true, element: <HomePage /> },
    { path: "ingredients", element: <IngredientsPage /> },
    { path: "recommendations", element: <RecommendationsPage /> },
    { path: "recipes/:id", element: <RecipeDetailPage /> },
    { path: "history", element: <HistoryPage /> },
  ],
}]);

export default function App() { return <RouterProvider router={router} />; }
