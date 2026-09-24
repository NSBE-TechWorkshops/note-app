import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { App } from "./App";
import { ConversationPage } from "./pages/ConversationPage";
import { CallbackPage } from "./pages/CallbackPage";
import { ListeningPage } from "./pages/ListeningPage";
import { ResponsePage } from "./pages/ResponsePage";
import { SettingsPage } from "./pages/SettingsPage";
import { ThinkingPage } from "./pages/ThinkingPage";

const rootRoute = createRootRoute({
  // note for you guys - this is the current page of the applications
  component: Outlet,
});

// base route when a user loads in
const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: App,
});

const listeningRoute = createRoute({ getParentRoute: () => rootRoute, path: "/listening", component: ListeningPage });
const thinkingRoute = createRoute({ getParentRoute: () => rootRoute, path: "/thinking", component: ThinkingPage });
const responseRoute = createRoute({ getParentRoute: () => rootRoute, path: "/response", component: ResponsePage });
const conversationRoute = createRoute({ getParentRoute: () => rootRoute, path: "/conversation", component: ConversationPage });
const callbackRoute = createRoute({ getParentRoute: () => rootRoute, path: "/callback", component: CallbackPage });
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings", component: SettingsPage });

const routeTree = rootRoute.addChildren([homeRoute, listeningRoute, thinkingRoute, responseRoute, conversationRoute, callbackRoute, settingsRoute]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
