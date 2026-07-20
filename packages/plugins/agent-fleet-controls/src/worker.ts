import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";

const plugin = definePlugin({
  async setup(ctx) {
    ctx.logger.info("Agent Fleet Controls ready");
  },

  async onHealth() {
    return { status: "ok", message: "Agent Fleet Controls is ready" };
  }
});

export default plugin;
runWorker(plugin, import.meta.url);
