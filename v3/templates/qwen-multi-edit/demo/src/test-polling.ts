/**
 * Test using polling mode (no WebSocket) - simpler for some use cases
 * 
 * Run: npx ts-node src/test-polling.ts
 */

import { Client } from "@stable-canvas/comfyui-client";
import * as fs from "fs";
import * as path from "path";

const API_HOST = "ybshiva--comfy-qwen-multi-edit-serve.modal.run";

const workflowPath = path.join(__dirname, "../../workflows/test-2511-api.json");
const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf-8"));

async function main() {
    console.log("=".repeat(60));
    console.log("ComfyUI Polling Mode Test (No WebSocket)");
    console.log("=".repeat(60));

    const client = new Client({
        api_host: API_HOST,
        ssl: true,
        fetch: fetch,
    });

    try {
        // Randomize seed
        const seed = Math.floor(Math.random() * 999999999);
        for (const nodeId in workflow) {
            if (workflow[nodeId].class_type === "KSampler") {
                workflow[nodeId].inputs.seed = seed;
            }
        }
        console.log(`🎲 Seed: ${seed}`);

        console.log("\n🚀 Running workflow (polling mode)...");
        const startTime = Date.now();

        // Use polling instead of WebSocket
        const result = await client.enqueue_polling(workflow);

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log(`\n✅ Completed in ${elapsed}s`);

        console.log("\n📸 Results:");
        if (result.images && result.images.length > 0) {
            for (let i = 0; i < result.images.length; i++) {
                const img = result.images[i];
                console.log(`   - Image ${i + 1}: type=${img.type}`);
                if (img.type === "url") {
                    console.log(`     URL: ${img.data}`);
                }
            }
        }

        console.log("\n" + "=".repeat(60));
        console.log("✅ POLLING TEST PASSED");
        console.log("=".repeat(60));

    } catch (error) {
        console.error("❌ Error:", error);
        process.exit(1);
    }
}

main();
