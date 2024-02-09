// Copyright Braid technologies ltd, 2024
import { expect } from 'expect';
import { describe, it } from 'mocha';

import { throwIfUndefined } from '../core/Asserts';
import { EEnvironment, Environment } from '../core/Environment';
import { Persona } from '../core/Persona';
import { Message } from '../core/Message';
import { Interest, NotificationFor } from '../core/NotificationFramework';
import { MessageBotFluidConnection } from '../core/MessageBotFluidConnection';
import { EIcon } from '../core/Icons';

var myId: string = "1234";
var myName: string = "Jon";
var myThumbnail: string = "abcd";
var myLastSeenAt = new Date();

class MockLocation { // Just create the fields we use in the Mock
   protocol: string;
   host: string;
   hostname: string;
   hash: string;
}

var mockLocation = new MockLocation();

async function wait() {
   await new Promise(resolve => setTimeout(resolve, 500));
}

function onAdd(interest_: Interest, notification_: NotificationFor<string>) : void {

}

function onChange(interest_: Interest, notification_: NotificationFor<string>): void {

}

function onRemove(interest_: Interest, notification_: NotificationFor<string>): void {

}

describe("Caucus", function () {

   this.timeout(10000);

   var newConnection: MessageBotFluidConnection;
   var persona: Persona;
   var id: string; 
   var oldEnv : EEnvironment; 

   var oldLocation: any = global.location;

   beforeEach(async () => {

      (global.location as any) = mockLocation;
      oldEnv = Environment.override (EEnvironment.kLocal);

      this.timeout(10000);
      persona = new Persona(myId, myName, EIcon.kPersonPersona, myThumbnail, myLastSeenAt);

      newConnection = new MessageBotFluidConnection({}, persona);

      let checked = process.env.JoinKey;
      throwIfUndefined(checked);
      id = await newConnection.createNew(checked);

      await wait();
   });

   afterEach(async () => {

      await wait();
      await newConnection.disconnect();

      Environment.override (oldEnv);      
      (global.location as any) = oldLocation;
   });

   it("Can create a valid caucus", async function () {

      var workingPersona: Persona = new Persona(persona);

      let caucus = newConnection.participantCaucus();

      caucus.add(workingPersona.id, workingPersona);
      expect(caucus.has(workingPersona.id)).toEqual(true);
      expect(caucus.get(workingPersona.id).equals(workingPersona)).toEqual(true);
      expect(caucus.current().size).toEqual(2); // The Bot perdona is added manually - size is alays >= 1

      workingPersona.name = "Joe";
      caucus.amend(workingPersona.id, workingPersona);
      expect(caucus.get(workingPersona.id).equals(workingPersona)).toEqual(true)

      caucus.remove(workingPersona.id);
      expect(caucus.has(workingPersona.id)).toEqual(false);
      expect(caucus.current().size).toEqual(1); // The Bot perdona is added manually - size is alays >= 1
    });

    it("Can detect invalid operations", async function () {

      var workingPersona: Persona = new Persona(persona);

      let caucus = newConnection.participantCaucus();

      caucus.add(workingPersona.id, workingPersona);

      let caught = false;
      try {
         caucus.get("banana");
      }
      catch {
         caught = true;            
      }

      expect(caught).toEqual(true);
    });

   it("Can synchronise", async function () {

      var workingPersona: Persona = new Persona(persona);

      let caucus = newConnection.participantCaucus();

      var synchMap: Map<string, Persona> = new Map<string, Persona>();

      // Sync down to no elements
      caucus.synchFrom(synchMap);
      expect(caucus.current().size === 0).toEqual(true);

      // Sync in a new element
      synchMap.set(workingPersona.id, workingPersona);
      caucus.synchFrom(synchMap);
      expect(caucus.current().size === 1).toEqual(true);
      expect(caucus.get(workingPersona.id).equals(workingPersona)).toEqual(true);

      // Sync in a changed element
      workingPersona.name = "Joe 2";
      caucus.synchFrom(synchMap);
      expect(caucus.current().size === 1).toEqual(true);
      expect(caucus.get(workingPersona.id).equals(workingPersona)).toEqual(true);
   });

   it("Can return an ordered array", async function () {

      // Create three Message objects
      var workingMessage: Message = new Message();
      var workingMessage2: Message = new Message();    
      var workingMessage3: Message = new Message(); 
      
      // Space them out a second apart
      let now = new Date();
      workingMessage2.sentAt = new Date(now.getTime() + 1000);
      workingMessage3.sentAt = new Date(now.getTime() + 2000);

      let caucus = newConnection.messageCaucus();

      var synchMap: Map<string, Message> = new Map<string, Message>();
      synchMap.set (workingMessage.id, workingMessage);
      synchMap.set (workingMessage2.id, workingMessage2);
      synchMap.set (workingMessage3.id, workingMessage3);

      // Sync in 3 elements     
      caucus.synchFrom(synchMap);
      expect(caucus.current().size === 3).toEqual(true);

      let tempArray = caucus.currentAsArray();

      expect(tempArray.length === 3).toEqual(true);
      expect(tempArray[0].sentAt.getTime() <= tempArray[1].sentAt.getTime()).toEqual(true);
      expect(tempArray[1].sentAt.getTime() <= tempArray[2].sentAt.getTime()).toEqual(true);
   });   
});

