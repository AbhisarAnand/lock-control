import { Mongo } from 'meteor/mongo';
import { Meteor } from 'meteor/meteor';

export const Locks = new Mongo.Collection("locks");

if (Meteor.isServer) {
    Meteor.publish("locks", function () {
        return Locks.find();
    });

    Meteor.methods({
        async "locks.toggle"(lockId) {
            console.log(`🔄 Received toggle request for lock ID: ${lockId}`);

            const lock = await Locks.findOneAsync(lockId);
            if (!lock) {
                console.error(`❌ Lock with ID ${lockId} not found`);
                throw new Meteor.Error("Lock not found");
            }

            const newStatus = lock.status === "Locked" ? "Unlocked" : "Locked";

            try {
                await Locks.updateAsync(lockId, { $set: { status: newStatus } });
                console.log(`✅ Lock ${lockId} updated to ${newStatus}`);
            } catch (error) {
                console.error(`❌ Error updating lock ${lockId}:`, error);
                throw new Meteor.Error("Database update failed", error.message);
            }
        }
    });
}