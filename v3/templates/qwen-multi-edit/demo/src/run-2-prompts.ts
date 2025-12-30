/**
 * Run 2 prompts with different seeds and save results
 * 
 * Run: npx tsx src/run-2-prompts.ts
 */

import { Client } from "@stable-canvas/comfyui-client";
import * as fs from "fs";
import * as path from "path";
import WebSocket from "ws";
import * as dotenv from "dotenv";

// Load environment variables from .env
dotenv.config({ path: path.join(__dirname, "../../../.env") });

const API_HOST = "ybshiva--comfy-qwen-multi-edit-serve.modal.run";
const workflowPath = path.join(__dirname, "../../workflows/test-2511-api.json");

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

async function runPrompt(client: Client, workflow: any, seed: number, name: string): Promise<string> {
    console.log(`\n🎲 Running "${name}" with seed: ${seed}`);

    // Clone workflow and set seed
    const wf = JSON.parse(JSON.stringify(workflow));
    for (const nodeId in wf) {
        if (wf[nodeId].class_type === "KSampler") {
            wf[nodeId].inputs.seed = seed;
        }
    }

    const startTime = Date.now();

    const result = await client.enqueue(wf, {
        progress: ({ max, value }) => {
            const pct = Math.round((value / max) * 100);
            process.stdout.write(`\r   Progress: ${value}/${max} (${pct}%)`);
        },
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`\n   ✅ Completed in ${elapsed}s`);

    // Get the image
    if (result.images && result.images.length > 0) {
        const img = result.images[0];

        if (img.type === "url") {
            // The SDK returns data like: https://host.modal.run/view?... (full URL)
            // OR it might return: /view?filename=...
            let imageUrl = img.data;
            if (!imageUrl.startsWith("http")) {
                imageUrl = `https://${API_HOST}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
            }
            console.log(`   📸 Downloading...`);

            const response = await authFetch(imageUrl);
            const buffer = Buffer.from(await response.arrayBuffer());

            const outputPath = path.join(__dirname, `../${name}.png`);
            fs.writeFileSync(outputPath, buffer);
            console.log(`   💾 Saved: ${outputPath} (${buffer.length} bytes)`);

            return outputPath;
        } else if (img.type === "buff") {
            // Already have buffer
            const outputPath = path.join(__dirname, `../${name}.png`);
            fs.writeFileSync(outputPath, Buffer.from(img.data));
            console.log(`   💾 Saved: ${outputPath}`);
            return outputPath;
        }
    }

    return "";
}

async function main() {
    console.log("=".repeat(60));
    console.log("🖼️  Running 2 Prompts with Different Seeds");
    console.log("=".repeat(60));

    // Load workflow
    const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf-8"));
    console.log(`Workflow: ${path.basename(workflowPath)}`);

    // Create client with auth
    const client = new Client({
        api_host: API_HOST,
        ssl: true,
        WebSocket: WebSocket as any,
        fetch: authFetch as typeof fetch,
    });

    try {
        console.log("\n🔌 Connecting...");
        await client.connect();
        console.log("✅ Connected!");

        // Generate two different seeds
        const seed1 = Math.floor(Math.random() * 999999999);
        const seed2 = Math.floor(Math.random() * 999999999);

        // Run prompt 1
        const image1 = await runPrompt(client, workflow, seed1, "version_1");

        // Run prompt 2
        const image2 = await runPrompt(client, workflow, seed2, "version_2");

        // Summary
        console.log("\n" + "=".repeat(60));
        console.log("📸 RESULTS");
        console.log("=".repeat(60));
        console.log(`\n   Version 1 (seed ${seed1}):`);
        console.log(`   → ${image1}`);
        console.log(`\n   Version 2 (seed ${seed2}):`);
        console.log(`   → ${image2}`);
        console.log("\n" + "=".repeat(60));

    } catch (error) {
        console.error("\n❌ Error:", error);
    } finally {
        client.close();
    }
}

main();
