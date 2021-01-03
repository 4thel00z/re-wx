"""
https://medium.com/@sweetpalma/gooact-react-in-160-lines-of-javascript-44e0742ad60f
"""
import functools
import wx
from inspect import isclass

from dispatch import dispatch, mount, update
from rewx.widgets import mount as _mount
from rewx.widgets import update as _update
from rewx.widgets import Block
mount.merge_registries(_mount._registry)
update.merge_registries(_update._registry)



def wsx(f):
    def convert(spec: list):
        type, props, *children = spec
        return create_element(type, props, children=list(map(convert, children)))
    # being used as a decorator
    if callable(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            result = f(*args, **kwargs)
            return convert(result)
        return inner
    else:
        return convert(f)


def create_element(type, props, children=None):
    element = {
        'type': type,
        'props': props
    }
    if children:
        if not isinstance(children, list):
            raise Exception('Children must be a list!')
        element['props']['children'] = children
    return element



def foo():
    wsx(
      ['block', {},
       ['statictext', {}]]
    )

def statictext2wx(element, parent):
    text = wx.StaticText(parent)
    text.SetLabel(element['props'].get('value'))
    if element['props'].get('on_click'):
        text.Bind(wx.EVT_LEFT_DOWN, element['props'].get('on_click'))
    text._type = element['type']
    return text

def block2wx(element, parent):
    panel = wx.Panel(parent)
    panel._type = element['type']
    box = wx.BoxSizer((element.get('props') or {}).get('orient', wx.VERTICAL))
    # for elm in element['props']['children']:
    #     wx_instance = render(elm, panel)
    #     box.Add(wx_instance, elm['props'].get('proportion', 0),
    #             elm['props'].get('flag', 0),
    #             elm['props'].get('border', 0))
    panel.SetSizer(box)
    return panel


def updatewx(instance, props):
    if isinstance(instance, wx.StaticText):
        instance: wx.StaticText = instance
        if props.get('on_click'):
            instance.Unbind(wx.EVT_LEFT_DOWN)
            instance.Unbind(wx.EVT_LEFT_DCLICK)
            instance.Bind(wx.EVT_LEFT_DOWN, props.get('on_click'))
            instance.Bind(wx.EVT_LEFT_DCLICK, props.get('on_click'))
        else:
            instance.Unbind(wx.EVT_LEFT_DCLICK)
            instance.Unbind(wx.EVT_LEFT_DOWN)
        instance.SetLabel(props.get('value', ''))
    elif isinstance(instance, wx.Panel):
        instance: wx.Panel = instance
        sizer: wx.BoxSizer = instance.GetSizer()
        sizer.SetOrientation(props.get('orient', wx.VERTICAL))
    return instance


def patch(dom: wx.Window, vdom):
    parent = dom.GetParent()
    try:
        # parent.Freeze()
        if isclass(vdom['type']) and issubclass(vdom['type'], Component):
            return Component.Patch(dom, vdom)
        # if type(vdom['type']) == type:
        #     return Component.Patch(dom, vdom)
        if not isinstance(dom, vdom['type']):
            for child in dom.GetChildren():
                dom.RemoveChild(child)
                child.Destroy()
            dom.Destroy()
            newdom = render(vdom, parent)
        elif isinstance(dom, vdom['type']):
            update(vdom, dom)
            pool = {f'__index_{index}': child for index, child in enumerate(dom.GetChildren())}
            for index, child in enumerate(vdom['props'].get('children', [])):
                key = f'__index_{index}'
                if key in pool:
                    patch(pool[key], child)
                else:
                    parent.RemoveChild(pool[key])
                    render(child, parent)
            newdom = dom
        else:
            raise Exception("unexpected case!")
        p = parent
        while p:
            p.Layout()
            p = p.GetParent()
        return newdom
    finally:
        parent.Update()
        pass
        # parent.Thaw()


class Component:
    def __init__(self, props):
        self.props = props
        self.state = None
        # this gets set dynamically once mounted / instantiated
        self.base = None

    @classmethod
    def Render(cls, vdom, parent=None):
        if cls.__name__ == vdom['type'].__name__:
            instance = vdom['type'](vdom['props'])
            instance.base = render(instance.render(), parent)
            instance.base._instance = instance
            instance.base._key = vdom['props'].get('key', None)
            instance.component_did_mount()
            return instance.base
        else:
            # TODO: what are the cases where this would be hit..?
            return render(vdom['type'](vdom['props']), parent)

    @classmethod
    def Patch(cls, dom, vdom):
        parent = dom.GetParent()
        # TODO: is any of this right..?
        if hasattr(dom, '_instance') and type(dom._instance).__name__ == vdom['type'].__name__:
            return patch(dom, dom._instance.render())
        if cls.__name__ == vdom['type'].__name__:
            return cls.Render(vdom, parent)
        else:
            return patch(dom, vdom['type'](vdom['props']))


    def component_did_mount(self):
        pass

    def render(self):
        return None

    def set_state(self, next_state):
        prev_state = self.state
        self.state = next_state
        patch(self.base, self.render())



def render(element, parent):
    if isclass(element['type']) and issubclass(element['type'], wx.Object):
        instance = mount(element, parent)
        for child in element['props'].get('children', []):
            sizer = instance.GetSizer()
            if not sizer:
                render(child, instance)
            else:
                sizer.Add(
                    render(child, instance),
                    child['props'].get('proportion', 0),
                    child['props'].get('flag', 0),
                    child['props'].get('border', 0)
                )
        return instance
    elif type(element['type']) == type:
        return element['type'].Render(element, parent)
    elif callable(element['type']):
        # stateless functional component
        return render(element['type'](element['props']), parent)
    else:
        instance: wx.Panel = block2wx(element, parent)
        sizer = instance.GetSizer()
        for child in element['props'].get('children'):
            sizer.Add(
                render(child, instance),
                child['props'].get('proportion', 0),
                child['props'].get('flag', 0),
                child['props'].get('border', 0)
            )
        return instance


if __name__ == '__main__':
    statictext = wx.StaticText

    foo_elm = create_element('block', {}, children=[
        create_element('statictext', {'value': 'Hey there, world!'}),
        create_element('statictext', {'value': 'Hey there, again!'}),
        create_element('block', {'orient': wx.HORIZONTAL}, children=[
            create_element('statictext', {'value': 'One'}),
            create_element('statictext', {'value': ' and Two!'}),
        ])
    ])

    foo_elm1 = create_element('block', {}, children=[
        create_element('statictext', {'value': 'One'}),
        create_element('statictext', {'value': 'Two'})
    ])

    foo_elm2 = create_element('block', {'orient': wx.HORIZONTAL}, children=[
        create_element('statictext', {'value': 'Two'}),
        create_element('statictext', {'value': 'One'}),
    ])

    # foo_elm3 = create_element(Foo, {'item1': 'HELLOOOOO'})
    # foo_elm4 = create_element(Bar, {})
    #
    # foo_elm5 = create_element(Bar, {'item1': 'HELLOOOOO'})
    # foo_elm6 = create_element(Foo, {'item1': 'BYeeeee'})

    # basic_app('My Hello App', foo_elm)
    import wx.lib.inspection
    app = wx.App()
    wx.lib.inspection.InspectionTool().Show()
    frame = wx.Frame(None, title='Test re-wx')
    frame.SetSize((570, 520))
    thing = render(create_element(statictext, {'label': 'Two'}), frame)
    # thing = patch(thing, foo_elm6)
    # t = Thread(target=andthen, args=(thing, foo_elm6))
    # t.start()
    box = wx.BoxSizer(wx.VERTICAL)
    box.Add(thing, 1, wx.EXPAND)
    frame.SetSizer(box)
    frame.Show()
    # frame.Fit()

    for child in frame.GetChildren():
        for ccc in child.GetChildren():
            for cc in ccc.GetChildren():
                cc.Layout()
            ccc.Layout()
        child.Layout()
    app.MainLoop()

