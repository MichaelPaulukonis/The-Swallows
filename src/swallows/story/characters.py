#!/usr/bin/env python

import random
import sys

from swallows.engine.objects import (
    Animate, ProperMixin, MasculineMixin, FeminineMixin,
    Topic,
    GreetTopic, SpeechTopic, QuestionTopic,
)
from swallows.util import pick

# TODO

# they check containers while someone else is in the room?  how'd that get that way?
# 'Hello, Alice', said Bob.  'Hello, Bob', replied Alice.  NEVER GETS OLD
# they should always scream at seeing the dead body.  the scream should
#   be heard throughout the house and yard.
# ...they check that the brandy is still in the liquor cabinet.  is this
#   really necessary?
# certain things can't be taken, but can be dragged (like the body)
# path-finder between any two rooms -- not too difficult, even if it
#   would be nicer in Prolog.
# "it was so nice" -- actually *have* memories of locations, and feelings
#   (good/bad, 0 to 10 or something) about memories
# anxiety memory = the one they're most recently panicked about
# memory of whether the revolver was loaded last time they saw it
# calling their bluff
# making a run for it when at gunpoint (or trying to distract them,
#   slap the gun away, scramble for it, etc)
# revolver might jam when they try to shoot it (maybe it should be a
#   pistol instead, as those can jam more easily)
# dear me, someone might actually get shot.  then what?  another dead body?


### some Swallows-specific topics (sort of)

class WhereQuestionTopic(Topic):
    pass


class ThreatGiveMeTopic(Topic):
    pass


class ThreatTellMeTopic(Topic):
    pass


class ThreatAgreeTopic(Topic):
    pass


### Base character personalities for The Swallows

class Character(Animate):
    def __init__(self, name, location=None, collector=None,
                 revolver=None, brandy=None, dead_body=None):
        """Constructor specific to characters.  In it, we set up some
        Swallows-specific properties ('nerves') and we set up some important
        items that this character needs to know about.  This is maybe
        a form of dependency injection.

        """
        Animate.__init__(self, name, location=location, collector=None)
        self.revolver = revolver
        self.brandy = brandy
        self.dead_body = dead_body
        # this should really be *derived* from having a recent memory
        # of seeing a dead body in the bathroom.  but for now,
        self.nerves = 'calm'

    def move_to(self, location):
        """Override some behaviour upon moving to a new location.

        """
        Animate.move_to(self, location)
        if random.randint(0, 10) == 0:
            self.emit("It was so nice being in <2> again",
             [self, self.location], excl=True)
        
        # okay, look around you.
        for x in self.location.contents:
            assert x.location == self.location
            if x == self:
                continue
            if x.horror():
                memory = self.recall(x)
                if memory:
                    amount = pick(['shudder', 'wave'])
                    emotion = pick(['fear', 'disgust', 'sickness', 'loathing'])
                    self.emit("<1> felt a %s of %s as <he-1> looked at <2>" % (amount, emotion), [self, x])
                    self.remember(x, self.location)
                else:
                    verb = pick(['screamed', 'yelped', 'went pale'])
                    self.emit("<1> %s at the sight of <indef-2>" % verb, [self, x], excl=True)
                    self.remember(x, self.location)
                    self.nerves = 'shaken'
            elif x.animate():
                other = x
                self.emit("<1> saw <2>", [self, other])
                other.emit("<1> saw <2> walk into the %s" % self.location.noun(), [other, self])
                self.remember(x, self.location)
                self.greet(x, "'Hello, <2>,' said <1>")
                for y in other.contents:
                    if y.treasure():
                        self.emit(
                            "<1> noticed <2> <was-2> carrying <indef-3>",
                            [self, other, y])
                        if self.revolver.location == self:
                            self.point_at(other, self.revolver)
                            self.address(other,
                                ThreatGiveMeTopic(self, subject=y),
                                "'Please give me <3>, <2>, or I shall shoot you,' <he-1> said",
                                [self, other, y])
                            return
                # another case of mind-reading.  well, it helps the story advance!
                # (it would help more to double-check this against your OWN memory)
                if self.revolver.location == self:
                    for thing in other.memories:
                        memory = other.recall(thing)
                        self_memory = self.recall(thing)
                        if self_memory:
                            continue
                        if memory.i_hid_it_there and memory.subject is not self.revolver:
                            self.point_at(other, self.revolver)
                            self.address(other,
                                ThreatTellMeTopic(self, subject=thing),
                                "'Tell me where you have hidden <3>, <2>, or I shall shoot you,' <he-1> said",
                                [self, other, thing])
                            return
            elif x.notable():
                self.emit("<1> saw <2>", [self, x])
                self.remember(x, self.location)

    def live(self):
        """Override some behaviour for taking a turn in the story.

        """
        # first, if in a conversation, turn total attention to that
        if self.topic is not None:
            return self.converse(self.topic)

        # otherwise, if there are items here that you desire, you *must* pick
        # them up.
        for x in self.location.contents:
            if x.treasure() or x.weapon() or x in self.desired_items:
                self.pick_up(x)
                return
        people_about = False

        # otherwise, fixate on some valuable object (possibly the revolver)
        # that you are carrying:
        fixated_on = None
        for y in self.contents:
            if y.treasure():
                fixated_on = y
                break
        if not fixated_on and random.randint(0, 20) == 0 and self.revolver.location == self:
            fixated_on = self.revolver

        # check if you are alone
        for x in self.location.contents:
            if x.animate() and x is not self:
                people_about = True

        choice = random.randint(0, 25)
        if choice < 10 and not people_about:
            return self.hide_and_seek(fixated_on)
        if choice < 20:
            return self.wander()
        if choice == 20:
            self.emit("<1> yawned", [self])
        elif choice == 21:
            self.emit("<1> gazed thoughtfully into the distance", [self])
        elif choice == 22:
            self.emit("<1> thought <he-1> heard something", [self])
        elif choice == 23:
            self.emit("<1> scratched <his-1> head", [self])
        elif choice == 24:
            self.emit("<1> immediately had a feeling something was amiss", [self])
        else:
            return self.wander()

    #
    # The following are fairly Swallows-specific methods.
    #

    def hide_and_seek(self, fixated_on):
        # check for some place to hide the thing you're fixating on
        containers = []
        for x in self.location.contents:
            if x.container():
                # did I hide something here previously?
                memories = []
                for thing in self.memories:
                    memory = self.recall(thing)
                    if memory.location == x:
                        memories.append(memory)
                containers.append((x, memories))
        if not containers:
            return self.wander()
        # ok!  we now have a list of containers, each of which has zero or
        # more memories of things being in it.
        if fixated_on:
            (container, memories) = pick(containers)
            self.emit("<1> hid <2> in <3>", [self, fixated_on, container])
            fixated_on.move_to(container)
            self.remember(fixated_on, container, i_hid_it_there=True)
            return self.wander()
        else:
            # we're looking for treasure!
            # todo: it would maybe be better to prioritize this selection
            (container, memories) = pick(containers)
            # sometimes, we don't care what we think we know about something
            # (this lets us, for example, explore things in hopes of brandy)
            if memories and random.randint(0, 3) == 0:
                memories = None
            if memories:
                memory = pick(memories)
                picking_up = random.randint(0, 5) == 0
                if memory.subject is self.revolver:
                    picking_up = True
                if picking_up:
                    if memory.i_hid_it_there:
                        self.emit("<1> retrieved <3> <he-1> had hidden in <2>",
                                  [self, container, memory.subject])
                    else:
                        self.emit("<1> retrieved <3> from <2>",
                                  [self, container, memory.subject])
                    # but!
                    if memory.subject.location != container:
                        self.emit("But <he-2> <was-2> missing", [self, memory.subject], excl=True)
                        # forget ALLLLLLL about it, then.  so realistic!
                        del self.memories[memory.subject]
                    else:
                        memory.subject.move_to(self)
                        self.remember(memory.subject, self)
                else:
                    self.emit("<1> checked that <3> <was-3> still in <2>",
                              [self, container, memory.subject])
                    # but!
                    if memory.subject.location != container:
                        self.emit("But <he-2> <was-2> missing", [self, memory.subject], excl=True)
                        del self.memories[memory.subject]
            else:  # no memories of this
                self.emit("<1> searched <2>", [self, container])
                desired_things = []
                for thing in container.contents:
                    # remember what you saw whilst searching this container
                    self.remember(thing, container)
                    if thing.treasure() or thing.weapon() or thing in self.desired_items:
                        desired_things.append(thing)
                if desired_things:
                    thing = pick(desired_things)
                    self.emit("<1> found <2> there, and took <him-2>", [self, thing])
                    thing.move_to(self)
                    self.remember(thing, self)

    def converse(self, topic):
        self.topic = None
        other = topic.originator
        if isinstance(topic, ThreatGiveMeTopic):
            found_object = None
            for x in self.contents:
                if x is topic.subject:
                    found_object = x
                    break
            if not found_object:
                self.speak_to(other,
                    "'But I don't have <3>!' protested <1>",
                    [self, other, topic.subject])
            else:
                self.speak_to(other,
                    "'Please don't shoot!', <1> cried",
                    [self, other, found_object])
                self.give_to(other, found_object)
        elif isinstance(topic, ThreatTellMeTopic):
            memory = self.recall(topic.subject)
            if not memory:
                self.speak_to(other,
                    "'I have no memory of that, <2>,' <1> replied",
                    [self, other, topic.subject])
            else:
                self.speak_to(other,
                    "'Please don't shoot!', <1> cried, '<he-3> <is-3> in <4>'",
                    [self, other, topic.subject, memory.location])
                # this is not really a *memory*, btw, it's a *belief*
                other.remember(topic.subject, memory.location)
        elif isinstance(topic, ThreatAgreeTopic):
            decision = self.what_to_do_about[topic.subject]
            self.speak_to(other,
               "'You make a persuasive case for remaining undecided, <2>,' said <1>",
               [self, other])
            del self.what_to_do_about[topic.subject]
            del other.other_decision_about[topic.subject]
        elif isinstance(topic, GreetTopic):
            # emit, because making this a speak_to leads to too much silliness
            self.emit("'Hello, <2>,' replied <1>", [self, other])
            # but otoh this sort of thing does not scale:
            other.emit("'Hello, <2>,' replied <1>", [self, other])
            # this needs to be more general
            self_memory = self.recall(self.dead_body)
            if self_memory:
                self.discuss(other, self_memory)
                return
            # this need not be *all* the time
            for x in other.contents:
                if x.notable():
                    self.remember(x, other)
                    self.speak_to(other, "'I see you are carrying <indef-3>,' said <1>", [self, other, x])
                    return
            choice = random.randint(0, 3)
            if choice == 0:
                self.question(other, "'Lovely weather we're having, isn't it?' asked <1>")
            if choice == 1:
                self.speak_to(other, "'I was wondering where you were,' said <1>")
        elif isinstance(topic, QuestionTopic):
            if topic.subject is not None:
                choice = random.randint(0, 1)
                if choice == 0:
                    self.speak_to(other, "'I know nothing about <3>, <2>,' explained <1>",
                       [self, other, topic.subject])
                if choice == 1:
                    self.speak_to(other, "'Perhaps, <2>,' replied <1>")
            else:
                self.speak_to(other, "'Perhaps, <2>,' replied <1>")
        elif isinstance(topic, WhereQuestionTopic):
            memory = self.recall(topic.subject)
            if not memory:
                self.speak_to(other,
                    "'I don't know,' <1> answered simply",
                    [self, other, topic.subject])
            elif memory.i_hid_it_there:
                self.question(other,
                    "'Why do you want to know where <3> is, <2>?'",
                    [self, other, topic.subject])
            elif topic.subject.location == self:
                self.speak_to(other,
                    "'I've got <3> right here, <2>'",
                    [self, other, topic.subject])
                self.put_down(topic.subject)
            else:
                if topic.subject.location.animate():
                    self.speak_to(other,
                        "'I think <3> has <4>,', <1> recalled",
                        [self, other, memory.location, topic.subject])
                else:
                    self.speak_to(other,
                        "'I believe it's in <3>, <2>,', <1> recalled",
                        [self, other, memory.location])
                # again, belief.  hearsay.  not a memory, really.
                other.remember(topic.subject, memory.location)
        elif isinstance(topic, SpeechTopic):
            choice = random.randint(0, 5)
            if choice == 0:
                self.emit("<1> nodded", [self])
            if choice == 1:
                self.emit("<1> remained silent", [self])
            if choice == 2:
                self.question(other, "'Do you really think so?' asked <1>")
            if choice == 3:
                self.speak_to(other, "'Yes, it's a shame really,' stated <1>")
            if choice == 4:
                self.speak_to(other, "'Oh, I know, I know,' said <1>")
            if choice == 5:
                # -- this is getting really annoying.  disable for now. --
                # item = pick(ALL_ITEMS)
                # self.question(other, "'But what about <3>, <2>?' posed <1>",
                #    [self, other, item], subject=item)
                self.speak_to(other, "'I see, <2>, I see,' said <1>")

    # this is its own method for indentation reasons
    def discuss(self, other, self_memory):
        # in general, characters should not be able to read each other's
        # minds.  however, it's convenient here.  besides, their face would
        # be pretty easy to read in this circumstance.
        other_memory = other.recall(self_memory.subject)
        if self_memory and not other_memory:
            self.question(other,
               "'Did you know there's <indef-3> in <4>?' asked <1>",
               [self, other, self_memory.subject, self_memory.location],
               subject=self_memory.subject)
            return
        if self_memory and other_memory:
            choice = random.randint(0, 2)
            if choice == 0:
                self.question(other, "'Do you think we should do something about <3>?' asked <1>",
                    [self, other, self_memory.subject])
            if choice == 1:
                self.speak_to(other, "'I think we should do something about <3>, <2>,' said <1>",
                    [self, other, self_memory.subject])
            if choice == 2:
                if self.nerves == 'calm':
                    self.decide_what_to_do_about(other, self_memory.subject)
                else:
                    if self.brandy.location == self:
                        self.emit("<1> poured <him-1>self a glass of brandy",
                            [self, other, self_memory.subject])
                        if self.brandy in self.desired_items:
                            self.desired_items.remove(self.brandy)
                        self.nerves = 'calm'
                        self.put_down(self.brandy)
                    elif self.recall(self.brandy):
                        self.speak_to(other,
                            "'I really must pour myself a drink,' moaned <1>",
                            [self, other, self_memory.subject],
                            subject=self.brandy)
                        self.desired_items.add(self.brandy)
                        if random.randint(0, 1) == 0:
                            self.address(other, WhereQuestionTopic(self, subject=self.brandy),
                                "'Where did you say <3> was?'",
                                [self, other, self.brandy])
                    else:
                        self.address(other, WhereQuestionTopic(self, subject=self.brandy),
                            "'Where is the brandy?  I need a drink,' managed <1>",
                            [self, other, self_memory.subject])
                        self.desired_items.add(self.brandy)

    # this is its own method for indentation reasons
    def decide_what_to_do_about(self, other, thing):
        phrase = {
            'call': 'call the police',
            'dispose': 'try to dispose of <3>'
        }
        # this should probably be affected by whether this
        # character has, oh, i don't know, put the other at
        # gunpoint yet, or not, or something
        if self.what_to_do_about.get(thing) is None:
            if random.randint(0, 1) == 0:
                self.what_to_do_about[thing] = 'call'
            else:
                self.what_to_do_about[thing] = 'dispose'

        if self.other_decision_about.get(thing, None) == self.what_to_do_about[thing]:
            self.question(other,
                ("'So we're agreed then, we should %s?' asked <1>" %
                  phrase[self.what_to_do_about[thing]]),
                [self, other, thing])
            # the other party might not've been aware that they agree
            other.other_decision_about[thing] = \
              self.what_to_do_about[thing]
        elif self.other_decision_about.get(thing, None) is not None:
            # WE DO NOT AGREE.
            if self.revolver.location == self:
                self.point_at(other, self.revolver)
                self.address(other,
                    ThreatAgreeTopic(self, subject=thing),
                    ("'I really feel *very* strongly that we should %s, <2>,' <he-1> said between clenched teeth" %
                     phrase[self.what_to_do_about[thing]]),
                    [self, other, thing])
            else:
                self.speak_to(other,
                    ("'I don't think it would be a good idea to %s, <2>,' said <1>" %
                    phrase[self.other_decision_about[thing]]),
                    [self, other, thing])
        else:
            self.speak_to(other,
                ("'I really think we should %s, <2>,' said <1>" %
                     phrase[self.what_to_do_about[thing]]),
                [self, other, thing])
            other.other_decision_about[thing] = \
              self.what_to_do_about[thing]


class MaleCharacter(MasculineMixin, ProperMixin, Character):
    pass


class FemaleCharacter(FeminineMixin, ProperMixin, Character):
    pass
