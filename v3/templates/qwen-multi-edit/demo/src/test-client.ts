/**
 * Test @stable-canvas/comfyui-client with our deployed ComfyUI
 * 
 * Run: npx tsx src/test-client.ts
 */

import { Client } from "@stable-canvas/comfyui-client";
import * as fs from "fs";
import * as path from "path";
import WebSocket from "ws";
import * as dotenv from "dotenv";

// Load environment variables from .env
dotenv.config({ path: path.join(__dirname, "../../../.env") });

// Our deployed ComfyUI server
const API_HOST = "ybshiva--comfy-qwen-multi-edit-serve.modal.run";

// Modal Proxy Auth headers
const MODAL_KEY = process.env.MODAL_TOKEN_ID;
const MODAL_SECRET = process.env.MODAL_TOKEN_SECRET;

if (!MODAL_KEY || !MODAL_SECRET) {
    console.error("❌ Missing MODAL_TOKEN_ID or MODAL_TOKEN_SECRET in .env");
    process.exit(1);
}

// Custom fetch with auth headers
const authFetch = (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
    return fetch(url, {
        ...init,
        headers: {
            ...init?.headers,
            "Modal-Key": MODAL_KEY!,
            "Modal-Secret": MODAL_SECRET!,
        },
    });
};

// Load workflow from file
const workflowPath = path.join(__dirname, "../../workflows/test-2511-api.json");
const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf-8"));

async function main() {
    console.log("=".repeat(60));
    console.log("ComfyUI Client Test (@stable-canvas/comfyui-client)");
    console.log("=".repeat(60));
    console.log(`Server: ${API_HOST}`);
    console.log(`Workflow: ${workflowPath}`);
    console.log(`Auth: Modal Proxy Auth ✅`);
    console.log("");

    // Create client with auth
    const client = new Client({
        api_host: API_HOST,
        ssl: true,
        WebSocket: WebSocket as any,
        fetch: authFetch as typeof fetch,
    });

    try {
        // Connect WebSocket
        console.log("🔌 Connecting...");
        await client.connect();
        console.log("✅ Connected!");

        // Check system stats
        console.log("\n📊 System Stats:");
        const stats = await client.getSystemStats();
        console.log(`   ComfyUI: ${stats.system.comfyui_version}`);
        console.log(`   PyTorch: ${stats.system.pytorch_version}`);
        stats.devices.forEach((d: any) => {
            console.log(`   GPU: ${d.name}`);
        });

        // Randomize seed
        const seed = Math.floor(Math.random() * 999999999);
        for (const nodeId in workflow) {
            if (workflow[nodeId].class_type === "KSampler") {
                workflow[nodeId].inputs.seed = seed;
                console.log(`\n🎲 Randomized seed: ${seed}`);
            }
        }

        // Queue and wait for result
        console.log("\n🚀 Running workflow...");
        const startTime = Date.now();

        const result = await client.enqueue(workflow, {
            progress: ({ max, value }) => {
                const pct = Math.round((value / max) * 100);
                process.stdout.write(`\r   Progress: ${value}/${max} (${pct}%)`);
            },
        });

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log(`\n\n✅ Completed in ${elapsed}s`);

        // Show results
        console.log("\n📸 Results:");
        if (result.images && result.images.length > 0) {
            for (let i = 0; i < result.images.length; i++) {
                const img = result.images[i];
                console.log(`   - Image ${i + 1}: type=${img.type}`);

                // Save image if it's buffer data
                if (img.type === "buff" && img.data) {
                    const outputPath = path.join(__dirname, `../output_${Date.now()}_${i}.png`);
                    fs.writeFileSync(outputPath, Buffer.from(img.data));
                    console.log(`   ✅ Saved: ${outputPath}`);
                } else if (img.type === "url" && img.data) {
                    console.log(`   URL: ${img.data}`);
                }
            }
        } else {
            console.log("   No images in result.images");
            console.log("   Checking result structure...");
            console.log(`   Keys: ${Object.keys(result)}`);
        }

        console.log("\n" + "=".repeat(60));
        console.log("✅ TEST PASSED");
        console.log("=".repeat(60));

    } catch (error) {
        console.error("\n❌ Error:", error);
        process.exit(1);
    } finally {
        client.close();
    }
}

main();
