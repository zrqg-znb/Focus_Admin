import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import svgr from "vite-plugin-svgr";

export default defineConfig({
	plugins: [
		react(),
		svgr({
			svgrOptions: {
				icon: true,
				exportType: "named",
				namedExport: "ReactComponent",
			},
		}),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
	test: {
		environment: "happy-dom",
		globals: true,
		include: ["src/**/*.{test,spec}.{ts,tsx}"],
	},
});
