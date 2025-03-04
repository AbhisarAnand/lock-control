import { Meteor } from "meteor/meteor";
import WebSocket, { WebSocketServer } from "ws";
import { Locks } from "/imports/api/locks"; // Import Locks collection
import { Random } from "meteor/random";

Meteor.startup(() => {
    console.log("🚀 Meteor WebSocket Server Starting...");

    const wss = new WebSocketServer({ port: 8080 });
    const HEARTBEAT_INTERVAL = 10000; // 10 seconds

    Locks.rawCollection().createIndex({ macAddress: 1 }, { unique: true }).catch((err) => {
        if (err.code !== 11000) { // Ignore duplicate key errors
            console.error("❌ Failed to create index:", err);
        }
    });


    wss.on("connection", (ws) => {
        console.log("🔗 New PicoW Connected");
        ws.send(JSON.stringify({ request: "SEND_MAC" })); // Ask PicoW for MAC

        ws.on("message", async (message) => {
            try {
                const data = JSON.parse(message);

                // ✅ Register MAC Address on first connect
                if (data.macAddress) {
                    console.log(`📡 Received MAC Address: ${data.macAddress}`);

                    const existingLock = await Locks.findOneAsync({ macAddress: data.macAddress });

                    if (!existingLock) {
                        try {
                            // Try inserting the new lock
                            const newLockId = `lock_${Random.id(5)}`;
                            await Locks.insertAsync({
                                _id: newLockId,
                                macAddress: data.macAddress,
                                name: `Lock_${newLockId}`,
                                status: "Locked",
                                lastSeen: new Date(),
                                connected: true
                            });
                            console.log(`🆕 New Lock Registered: Lock_${newLockId} (MAC: ${data.macAddress})`);
                        } catch (err) {
                            if (err.code === 11000) {
                                console.warn(`⚠️ Lock with MAC ${data.macAddress} already exists, skipping insertion.`);
                            } else {
                                console.error("❌ Error inserting lock:", err);
                            }
                        }
                    } else {
                        // Update existing lock
                        await Locks.updateAsync({ macAddress: data.macAddress }, { $set: { lastSeen: new Date(), connected: true } });
                        console.log(`✅ Lock ${existingLock.name} is active. Updated lastSeen.`);
                    }
                }

                // ✅ Handle normal lock/unlock commands
                if (data.command) {
                    console.log(`📩 Received Command: ${data.command} for MAC: ${data.macAddress}`);
                    await Locks.updateAsync(
                        { macAddress: data.macAddress },
                        { $set: { status: data.command } }
                    );
                }

                // ✅ Handle PONG response from PicoW
                if (data.response === "PONG") {
                    await Locks.updateAsync({ macAddress: data.macAddress }, { $set: { lastSeen: new Date(), connected: true } });
                    console.log(`✅ Lock ${data.macAddress} responded to heartbeat.`);
                }

            } catch (err) {
                console.error("❌ Error processing message:", err);
            }
        });

        ws.on("close", () => {
            console.log("❌ A PicoW Disconnected");
        });
    });

    // 🔄 Periodically send heartbeats to all locks
    setInterval(async () => {
        const locks = await Locks.find().fetch();

        locks.forEach(async (lock) => {
            if (lock.connected) {
                console.log(`📡 Sending PING to ${lock.macAddress}`);
                wss.clients.forEach((client) => {
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(JSON.stringify({ request: "PING", macAddress: lock.macAddress }));
                    }
                });

                // If no response within timeout, mark as disconnected
                setTimeout(async () => {
                    const updatedLock = await Locks.findOneAsync({ macAddress: lock.macAddress });

                    // ✅ Check if the lock still exists before accessing lastSeen
                    if (!updatedLock || !updatedLock.lastSeen) {
                        console.log(`⚠️ Lock ${lock.macAddress} no longer exists, skipping...`);
                        return;
                    }

                    if (updatedLock.lastSeen < new Date(Date.now() - HEARTBEAT_INTERVAL)) {
                        await Locks.updateAsync({ macAddress: lock.macAddress }, { $set: { connected: false } });
                        console.log(`❌ Lock ${lock.macAddress} marked as disconnected (no heartbeat response).`);
                    }
                }, HEARTBEAT_INTERVAL);
            }
        });
    }, HEARTBEAT_INTERVAL);

    // ✅ Function to send lock/unlock commands via WebSocket
    Meteor.methods({
        async "locks.sendCommand"(macAddress, command) {
            console.log(`🔐 Sending ${command} command to Lock (MAC: ${macAddress})`);

            // Fetch lock
            const lock = await Locks.findOneAsync({ macAddress });
            if (!lock) {
                console.log(`⚠️ No lock found with MAC ${macAddress}!`);
                return;
            }

            // Send WebSocket message
            const message = JSON.stringify({ macAddress, command });
            console.log(`📤 WebSocket Message: ${message}`);

            let sent = false;
            wss.clients.forEach((client) => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(message);
                    sent = true;
                }
            });

            if (!sent) {
                console.log(`⚠️ No active WebSocket clients found for MAC: ${macAddress}`);
            } else {
                console.log(`✅ Command successfully sent to ${macAddress}`);
            }

            // Update MongoDB with new status
            await Locks.updateAsync({ macAddress }, { $set: { status: command, lastSeen: new Date() } });
        },

        // ✅ Remove lock manually
        async "locks.removeLock"(macAddress) {
             console.log(`🗑️ Removing lock with MAC: ${macAddress}`);

            // Find WebSocket client for this PicoW
            let clientToClose = null;
            wss.clients.forEach((client) => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify({ macAddress, command: "DISCONNECT" })); // Tell PicoW to disconnect
                    clientToClose = client;
                }
            });

            // Close the WebSocket connection
            if (clientToClose) {
                console.log(`🔌 Closing WebSocket connection for ${macAddress}`);
                clientToClose.close();
            }

            const result = await Locks.removeAsync({ macAddress });
            console.log(`✅ Lock ${macAddress} removed from database.`);

            // Prevent re-adding the same lock too quickly
            setTimeout(async () => {
                const checkLock = await Locks.findOneAsync({ macAddress });
                if (!checkLock) {
                    console.log(`🔒 Lock ${macAddress} successfully removed and not re-added.`);
                } else {
                    console.warn(`⚠️ Lock ${macAddress} reappeared after removal!`);
                }
            }, 5000);

            return result;
        },

        async "locks.updateLockName"(macAddress, newName) {
            console.log(`✏️ Updating lock name for MAC: ${macAddress} to "${newName}"`);

            const lock = await Locks.findOneAsync({ macAddress });
            if (!lock) {
                throw new Meteor.Error("not-found", "Lock not found");
            }

            await Locks.updateAsync({ macAddress }, { $set: { name: newName } });
            console.log(`✅ Lock name updated to: ${newName}`);
        }
    });

    console.log("✅ WebSocket Server Running on ws://localhost:8080");
});
