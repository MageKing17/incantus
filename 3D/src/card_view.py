#!/usr/bin/env python

'''
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id: $'

import pyglet
from pyglet.gl import *

import anim
import euclid
import GUIEvent
from widget import Widget, Label
from anim_euclid import BezierPath
from game.pydispatch import dispatcher

sixteenfv = GLfloat*16

import math
import CardLibrary

class CardView(Widget):
    focus_size = 1.0 #0.8
    def __init__(self, pos, reverse_draw=False):
        super(CardView,self).__init__(pos)
        self.cards = []
        self.focus_idx = 0
        self.focus_dir = 1
        self.visible = 0
        self.reverse_draw = reverse_draw
        self.pos_transition = "ease_out_back"
        self.orientation_transition = "sine"
    def clear(self):
        self.cards = []
        self.focus_idx = 0
        self.focus_dir = 1
    def show(self):
        super(CardView,self).show()
        for c in self.cards: c.alpha = 1.0
    def hide(self):
        super(CardView,self).hide()
        for c in self.cards: c.alpha = 0.0

    focused = property(fget=lambda self: self.cards[self.focus_idx])

    def focus_next(self):
        if self.visible == 1 and self.focus_idx < len(self)-1:
            dispatcher.send(GUIEvent.FocusCard())
            self.focus_dir = 1
            self.focus_idx += self.focus_dir
            self.layout()
            return True
        else: return False
    def focus_previous(self):
        if self.visible == 1 and self.focus_idx > 0:
            dispatcher.send(GUIEvent.FocusCard())
            self.focus_dir = -1
            self.focus_idx += self.focus_dir
            self.layout()
            return True
        else: return False
    def render_after_transform(self):
        if not self.reverse_draw:
            for card in self.cards: card.draw()
        else:
            for card in self.cards[::-1]: card.draw()
    def __len__(self): return len(self.cards)

class HandView(CardView):
    def __init__(self, pos=euclid.Vector3(0,0,0)):
        super(HandView,self).__init__(pos, reverse_draw=True)
        self._pos.set_transition(dt=0.5, method="ease_out_back")
        self.small_size = 0.6
        self.played = []
        self.focus_idx = 0
    def show(self):
        #self.focus_idx = len(self)/2
        self.layout()
        if self.visible == 0:
            self.old_pos = self.pos
            self.pos += euclid.Vector3(0,325,0)
        super(HandView,self).show()
    def hide(self):
        self.pos = self.old_pos
        for card in self.cards: card.alpha = anim.animate(1,0,dt=1.5, method="ease_out_circ")
        super(HandView,self).hide()
    def add_card(self, card):
        newcard = CardLibrary.CardLibrary.getCard(card)
        newcard._pos.set_transition(dt=0.4, method=self.pos_transition)
        newcard._orientation.set_transition(dt=0.2, method=self.orientation_transition)
        newcard.size = anim.animate(newcard.size, newcard.size, dt=0.2, method="sine")
        newcard.alpha = anim.animate(0, 0, dt=3.0, method="ease_out_circ")
        self.cards.append(newcard)
        self.layout()
    def remove_card(self, card):
        card = CardLibrary.CardLibrary.getCard(card)
        # XXX This if statement is an ugly hack, I should remove it once I figure out
        # how to place cards from hand to the stack
        if card in self.cards:
            self.cards.remove(card)
            if self.focus_dir < 0: self.focus_idx += self.focus_dir
            if self.focus_idx > len(self)-1: self.focus_idx = len(self)-1
            elif self.focus_idx < 0: self.focus_idx = 0
            self.layout()
    def card_on_stack(self, ability):
        # XXX This is a big ugly hack
        from game.Ability import CastSpell
        if not isinstance(ability, CastSpell): return
        card = CardLibrary.CardLibrary.getCard(ability.card)
        if card in self.cards:
            self.cards.remove(card)
            if self.focus_dir < 0: self.focus_idx += self.focus_dir
            if self.focus_idx > len(self)-1: self.focus_idx = len(self)-1
            elif self.focus_idx < 0: self.focus_idx = 0
            self.played.append(card)
            self.layout()
    def card_off_stack(self, ability):
        # XXX This is a big ugly hack
        from game.Ability import CastSpell
        if not isinstance(ability, CastSpell): return
        card = CardLibrary.CardLibrary.getCard(ability.card)
        if card in self.played:
            self.played.remove(card)
            self.cards.append(card)
            self.layout()
    def layout_original(self):
        if len(self) > 0:
            if self.focus_idx == -1: self.focus_idx = len(self)-1
            cards = self.cards
            w, h = cards[0].width, cards[0].height
            radius = h*1.5
            incr_arc = math.pi/180*-2
            extra_arc = math.pi/180*-27
            Q = euclid.Quaternion.new_rotate_axis(incr_arc*(self.focus_idx-1)+extra_arc, euclid.Vector3(0,0,-1))
            i = 0.001
            for card in cards[:self.focus_idx]:
                card.orientation = Q
                card.pos = Q*euclid.Vector3(0,radius,0) - euclid.Vector3(0,radius,i)
                card.size = self.small_size
                Q.rotate_axis(incr_arc, euclid.Vector3(0,0,1))
                i += 0.001
            card = cards[self.focus_idx]
            card.pos = euclid.Vector3(0,0,i)
            i += 0.001
            card.orientation = euclid.Quaternion()
            card.size = self.focus_size
            Q = euclid.Quaternion.new_rotate_axis(-extra_arc, euclid.Vector3(0,0,-1))
            for card in cards[self.focus_idx+1:]:
                card.orientation = Q 
                card.pos = Q*euclid.Vector3(0,radius,0) - euclid.Vector3(0,radius,i)
                card.size = self.small_size
                Q.rotate_axis(incr_arc, euclid.Vector3(0,0,1))
                i += 0.001
    def layout_staggered(self):
        if len(self) > 0:
            if self.focus_idx == -1: self.focus_idx = len(self)-1
            cards = self.cards
            w, h = cards[0].width, cards[0].height
            radius = h*8#1.5
            incr_arc = math.pi/180*-0.75 #1
            extra_arc = math.pi/180*-4.5 #10 #-27
            Q = euclid.Quaternion.new_rotate_axis(incr_arc*(self.focus_idx-1)+extra_arc, euclid.Vector3(0,0,-1))
            i = 0.001
            y_incr = (self.focus_idx-1)*h*0.1*self.small_size
            size = self.small_size
            for card in cards[:self.focus_idx]:
                card.orientation = Q
                card.pos = Q*euclid.Vector3(0,radius,0) - euclid.Vector3(0,radius+y_incr,i)
                card.size = size
                Q.rotate_axis(incr_arc, euclid.Vector3(0,0,1))
                y_incr -= h*0.1*size
                #if size < self.small_size: size += 0.05
                i += 0.001
            card = cards[self.focus_idx]
            card.pos = euclid.Vector3(0,0,i)
            i += 0.001
            card.orientation = euclid.Quaternion()
            card.size = self.focus_size
            #Q = euclid.Quaternion.new_rotate_axis(incr_arc*(len(self)-self.focus_idx)+extra_arc, euclid.Vector3(0,0,1))
            #incr_arc *= -1
            #y_incr = (len(self)-self.focus_idx-1)*h*0.1*self.small_size
            Q = euclid.Quaternion.new_rotate_axis(-extra_arc, euclid.Vector3(0,0,-1))
            y_incr += h*0.1*self.small_size
            #for card in cards[-1:self.focus_idx:-1]:
            for card in cards[self.focus_idx+1:]:
                card.orientation = Q
                card.pos = Q*euclid.Vector3(0,radius,0) - euclid.Vector3(0,radius+y_incr,i)
                card.size = self.small_size
                Q.rotate_axis(incr_arc, euclid.Vector3(0,0,1))
                y_incr += h*0.1*self.small_size
                i += 0.001
    layout = layout_staggered
    def render_after_transform(self):
        for card in self.cards[self.focus_idx::-1]: card.draw()
        for card in self.cards[self.focus_idx+1:]: card.draw()

from game.Ability.CastingAbility import CastSpell
class StackView(CardView):
    width = anim.Animatable()
    height = anim.Animatable()
    def __init__(self, pos=euclid.Vector3(0,0,0)):
        super(StackView,self).__init__(pos)
        self.is_focused = False
        self.visible = anim.constant(0)
        self.header = Label("Stack", halign="left", valign="top")
        self.header.pos = euclid.Vector3(0,0,0)
        self.text = Label("", halign="left", valign="center", background=True)
        self.width = anim.animate(0, 0, dt=0.4, method="sine")
        self.height = anim.animate(0, 0, dt=0.4, method="sine")
        self.layout()
    def add_ability(self, ability, startt=0):
        if ability.card == "Assign Damage":
            newcard = CardLibrary.CardLibrary.getFakeCard(ability)
            newcard.triggered = True
        else:
            triggered = not isinstance(ability, CastSpell)
            newcard = CardLibrary.CardLibrary.getStackCard(ability.card, triggered)
        newcard.ability = ability
        self.cards.append(newcard)
        self.focus_idx = len(self)-1
        self.layout()
        newcard._pos.set_transition(dt=0.5, method=self.pos_transition)
        #newcard.size = anim.animate(newcard.size, newcard.size, dt=0.2, method="sine")
        newcard.alpha = anim.animate(0, 1, startt=startt, dt=1.0, method="ease_out_circ")
        if startt != 0: newcard.visible = anim.animate(0,1,dt=startt, method="step")
        return newcard
    def remove_ability(self, ability):
        for idx, card in enumerate(self.cards):
            if ability == card.ability:
                self.cards.remove(card)
                if self.focus_idx >= len(self): self.focus_idx = len(self)-1
                break
        else: raise Exception
        self.layout()
    def get_card(self, ability):
        for card in self.cards:
            if ability == card.ability: return card
        else: return None
    def focus(self):
        self.is_focused = True
        self.focus_idx = len(self)-1
        self.layout()
    def unfocus(self):
        self.is_focused = False
        self.unfocused_layout()
    def layout(self):
        if self.is_focused: self.focused_layout()
        else: self.unfocused_layout()
    def unfocused_layout(self):
        size = 0.25
        self.text.visible = anim.animate(0.0, 0.0, dt=0.1)
        if len(self.cards):
            self.visible = 1.0
            self.header.visible = 1.0
            card = self.cards[0]
            x_incr, y_incr = card.width*size*0.15, -card.height*size*0.10
            x, y = card.width*size/2, -self.header.height-card.height*size/2
            z = 0
            for card in self.cards:
                card.size = size
                card.pos = euclid.Vector3(x,y,z)
                x += x_incr
                y += y_incr
                z += 0.001
            self.width = x + card.width*size/2
            self.height = y - card.height*size/2
        else:
            self.visible = 0
    def focused_layout(self):
        min_size = 0.2
        self.header.visible = 0
        if len(self) > 0:
            self.visible = 1.0
            w, h = self.cards[0].width, self.cards[0].height
            x_incr = w*0.025
            y_incr = h*0.025
            startx, starty = 20, -20
            x = startx-self.focus_idx*x_incr
            y = starty+(self.focus_idx-1)*y_incr
            z = 0.001
            for i, card in enumerate(self.cards[:self.focus_idx]):
                card.size = min_size
                card.pos = euclid.Vector3(x,y,z)
                x += x_incr
                y -= y_incr
                z += 0.001
            card = self.cards[self.focus_idx]
            card.size = anim.animate(card.size, self.focus_size, dt=0.2, method="sine")
            card.pos = euclid.Vector3(startx+w*0.45, y-h*0.4, z)
            self.text.visible = 1.0
            #if card.triggered: self.text.visible = 1.0
            #else: self.text.visible = 0.0
            self.text.pos = euclid.Vector3(startx, y-h*0.7, z)
            self.text.set_text(str(card.ability), width=0.9*w)
            x -= x_incr*4
            y -= h*0.8
            z += 0.001
            for i, card in enumerate(self.cards[self.focus_idx+1:]):
                card.size = min_size
                card.pos = euclid.Vector3(x,y,z)
                x -= x_incr
                y -= y_incr
                z += 0.001
        else:
            self.visible = 0
    def render_after_transform(self):
        if self.header.visible == 1.0:
            glColor4f(1.0,0,0, 0.3)
            glDisable(GL_TEXTURE_2D)
            glBegin(GL_QUADS)
            glVertex3f(-10, 5, 0)
            glVertex3f(self.width+10, 5, 0)
            glVertex3f(self.width+10, self.height-10, 0)
            glVertex3f(-10, self.height-10, 0)
            glEnd()
            self.header.render()
        super(StackView,self).render_after_transform()
        self.text.render()

class ZoneView(CardView):
    def __init__(self, pos=euclid.Vector3(0,0,0)):
        super(ZoneView,self).__init__(pos,reverse_draw=True)
        self._pos.set_transition(dt=0.001)
        self.sorted = False
        self.dir = 1
        points = [(0.0, 0.0), (26.0, 244.0), (184.0, 368.0), (400.0, 226.0)]
        self.path = BezierPath(*[euclid.Point2(v[0], v[1]) for v in points])
        self.visible = anim.animate(0,0,dt=0.3)
    def build(self, zone, is_opponent):
        self.cards = []
        self.selected = []
        if is_opponent: self.dir = -1
        else: self.dir = 1
        for card in zone: self.add_card(card)
        self.orig_order = dict([(c.gamecard.key, i) for i, c in enumerate(self.cards)])
        self.focus_idx = 0
        self.layout()
    def focus_next(self):
        if self.dir == 1: cond = (self.focus_idx < len(self)-1)
        else: cond = self.focus_idx > 0
        if self.visible == 1 and cond: #self.focus_idx < len(self)-1:
            dispatcher.send(GUIEvent.FocusCard())
            self.focus_dir = self.dir
            self.focus_idx += self.focus_dir
            self.layout()
            return True
        else: return False
    def focus_previous(self):
        if self.dir == 1: cond = self.focus_idx > 0
        else: cond = self.focus_idx < len(self)-1
        if self.visible == 1 and cond: #self.focus_idx > 0:
            dispatcher.send(GUIEvent.FocusCard())
            self.focus_dir = -self.dir
            self.focus_idx += self.focus_dir
            self.layout()
            return True
        else: return False
    def toggle_sort(self):
        if self.sorted:
            self.sorted = False
            self.cards.sort(key=lambda c: self.orig_order[c.gamecard.key])
            self.layout()
        else:
            self.sorted = True
            self.cards.sort(key=lambda c: str(c))
            self.layout()
    def add_card(self, card):
        newcard = CardLibrary.CardLibrary.getCardCopy(card)
        newcard._pos.set_transition(dt=0.5, method=self.pos_transition)
        newcard._orientation.set(euclid.Quaternion())
        newcard._orientation.set_transition(dt=0.2, method=self.orientation_transition)
        newcard.size = anim.animate(0.1, 0.1, dt=0.2, method="sine")
        newcard.alpha = anim.animate(0, 1, dt=1.0, method="ease_out_circ")
        self.cards.append(newcard)
    def select_card(self):
        card = self.focused
        self.cards.remove(card)
        self.selected.append(card)
        if self.focus_dir < 0: self.focus_idx += self.focus_dir
        if self.focus_idx > len(self)-1: self.focus_idx = len(self)-1
        elif self.focus_idx < 0: self.focus_idx = 0
        self.layout()
        self.layout_selected()
    def deselect_card(self, card):
        self.selected.remove(card)
        self.cards.insert(0, card) # Find the right position to reinsert
        self.layout()
        self.layout_selected()
    def handle_click(self, x, y):
        size = self.focus_size / 4.
        for card in self.selected:
            sx, sy, sw, sh = card.pos.x, card.pos.y, card.width*size, card.height*size
            if x > sx-sw and x < sx+sw and y >= sy-sh and y <= sy+sh:
                return card
        else: return None
    def show(self):
        super(ZoneView,self).show()
    def hide(self):
        self.visible = 0.0
        for card in self.cards:
            card.alpha = 0.5
            #card._pos.set_transition(dt=0.25, method="ease_out_circ")
            card.pos = euclid.Vector3(0,0,0)
            card.size = anim.animate(card.size, 0.1, dt=0.25, method="ease_out_circ")
        for card in self.selected:
            card.alpha = 0.5
            #card._pos.set_transition(dt=0.25, method="ease_out_circ")
            card.pos = euclid.Vector3(0,0,0)
            card.size = anim.animate(card.size, 0.1, dt=0.25, method="ease_out_circ")
    def layout_selected(self):
        dir = self.dir
        i = 0.001
        x = 0
        size = self.focus_size / 2
        for card in self.selected:
            card.size = size
            y = card.height*(1+size/2)*dir
            card.pos = euclid.Vector3(x, y,i)
            x += card.width*size*1.1*dir
            i+=0.001
    def layout_straight(self):
        numcards = len(self)
        if numcards > 0:
            cards = self.cards
            dir = self.dir
            i = 0.001
            x = y = 0
            #x -= cards[0].width*self.focus_size*0.6*dir
            for card in cards[:self.focus_idx]:
                card.size = 0.25
                x += card.width*0.25*0.1*dir
                card.pos = euclid.Vector3(x, y+card.height*0.125*dir,i)
                i += 0.001
            card = cards[self.focus_idx]
            card.size = self.focus_size
            x += card.width*self.focus_size*0.5*dir
            card.pos = euclid.Vector3(x, y+card.height*self.focus_size/2*dir,i)
            x += card.width*self.focus_size*0.5*dir
            i += 0.001
            for card in cards[self.focus_idx+1:]:
                card.size = 0.25
                x += card.width*0.25*0.1*dir
                card.pos = euclid.Vector3(x, y+card.height*0.125*dir,i)
                i += 0.001
    def layout_bezier(self):
        numcards = len(self)
        if numcards > 0:
            cards = self.cards
            path_param = 1./numcards
            cardcounter = 0
            i = 0.001
            for card in cards[:self.focus_idx]:
                point = self.path.get(cardcounter*path_param)
                card.pos = euclid.Vector3(point.x, point.y,i)
                card.size = 0.25
                i += 0.001
                cardcounter += 1
            card = cards[self.focus_idx]
            point = self.path.get(cardcounter*path_param)
            card.pos = euclid.Vector3(point.x, point.y,i)
            card.size = 0.25
            cardcounter += 1
            i += 0.001
            for card in cards[self.focus_idx+1:]:
                point = self.path.get(cardcounter*path_param)
                card.pos = euclid.Vector3(point.x, point.y,i)
                card.size = 0.25
                i += 0.001
                cardcounter += 1
    layout = layout_straight
    def render_after_transform(self):
        #if not self.reverse_draw:
        #    for card in self.cards: card.draw()
        #else:
        #    for card in self.cards[::-1]: card.draw()
        if self.cards:
            for card in self.cards[:self.focus_idx]: card.draw()
            for card in self.cards[-1:self.focus_idx:-1]: card.draw()
            self.focused.draw()
        for card in self.selected: card.draw()
