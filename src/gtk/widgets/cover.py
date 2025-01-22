# SPDX-FileCopyrightText: 2022  Emmanuele Bassi
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk, Gio, GLib, Gtk, GObject, Graphene, Gsk

class CoverSize(GLib.Enum):
    LARGE = 0
    SMALL = 1

    def __str__(self):
        if self == CoverSize.LARGE:
            return "large"
        elif self == CoverSize.SMALL:
            return "small"

class CoverPicture(GObject.Object):
    __gproperties__ = {
        'cover': (Gdk.Texture, 'Cover', 'The cover image', GObject.ParamFlags.READWRITE),
        'cover-size': (CoverSize, 'Cover size', 'The size of the cover', GObject.ParamFlags.READWRITE)
    }

    LARGE_SIZE = 192
    SMALL_SIZE = 48

    def __init__(self):
        super().__init__()
        self.cover = None
        self.cover_size = CoverSize.LARGE
        self.set_property('css_name', 'picture')
        self.set_property('accessible_role', Gtk.AccessibleRole.IMG)
        self.add_css_class('cover')
        self.set_property('overflow', Gtk.Overflow.HIDDEN)
        self.connect('notify::scale-factor', self.on_scale_factor_notify)

    def do_get_property(self, property):
        if property.name == 'cover':
            return self.cover
        elif property.name == 'cover-size':
            return self.cover_size

    def do_set_property(self, property, value):
        if property.name == 'cover':
            self.cover = value
        elif property.name == 'cover-size':
            self.cover_size = value

    def on_scale_factor_notify(self, *args):
        self.queue_draw()

    def do_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_measure(self, orientation, for_size):
        if self.cover_size == CoverSize.LARGE:
            return (self.LARGE_SIZE, self.LARGE_SIZE, -1, -1)
        elif self.cover_size == CoverSize.SMALL:
            return (self.SMALL_SIZE, self.SMALL_SIZE, -1, -1)

    def do_snapshot(self, snapshot):
        if self.cover:
            scale_factor = self.get_scale_factor()
            width = self.get_allocated_width() * scale_factor
            height = self.get_allocated_height() * scale_factor
            ratio = self.cover.get_intrinsic_aspect_ratio()
            if ratio > 1.0:
                w = width
                h = width / ratio
            else:
                w = height * ratio
                h = height
            x = (width - w) / 2.0
            y = (height - h) / 2.0
            snapshot.scale(1.0 / scale_factor, 1.0 / scale_factor)
            snapshot.translate(Graphene.Point(x, y))
            snapshot.append_scaled_texture(self.cover, Gsk.ScalingFilter.TRILINEAR, Graphene.Rect(0.0, 0.0, w, h))

    def set_cover(self, cover):
        if cover:
            self.cover = cover
        else:
            self.cover = None
        self.queue_draw()
        self.notify('cover')

    def set_cover_size(self, cover_size):
        self.cover_size = cover_size
        self.queue_resize()
        self.notify('cover-size')
