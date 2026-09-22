import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { App } from "./App";

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

const routeTree = rootRoute.addChildren([homeRoute]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
