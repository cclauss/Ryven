from NENV import *
widgets = import_widgets(__file__)


# from ryvencore_qt import Node


class NodeBase(Node):
    pass


class DualNodeBase(Node):
    """For nodes that can be active and passive"""

    def __init__(self, params, active=True):
        super().__init__(params)

        self.active = active
        if active:
            self.special_actions['make passive'] = {'method': self.make_passive}
        else:
            self.special_actions['make active'] = {'method': self.make_active}

    def make_passive(self):
        del self.special_actions['make passive']

        self.delete_input(0)
        self.delete_output(0)
        self.active = False

        self.special_actions['make active'] = {'method': self.make_active}

    def make_active(self):
        del self.special_actions['make active']

        self.create_input('exec', insert=0)
        self.create_output('exec', insert=0)
        self.active = True

        self.special_actions['make passive'] = {'method': self.make_passive}

    def get_state(self) -> dict:
        return {
            'active': self.active
        }

    def set_state(self, data: dict):
        self.active = data['active']


# -------------------------------------------


class Button_Node(NodeBase):
    title = 'Button'
    main_widget_class = widgets.ButtonNode_MainWidget
    main_widget_pos = 'between ports'
    init_inputs = [

    ]
    init_outputs = [
        NodeOutputBP('exec')
    ]
    color = '#99dd55'

    def update_event(self, input_called=-1):
        self.exec_output(0)


class Print_Node(DualNodeBase):
    title = 'Print'
    init_inputs = [
        NodeInputBP(type_='exec'),
        NodeInputBP(dtype=dtypes.Data(size='m')),
    ]
    init_outputs = [
        NodeOutputBP(type_='exec'),
    ]
    color = '#5d95de'

    def __init__(self, params):
        super().__init__(params, active=True)

    def update_event(self, input_called=-1):
        if self.active and input_called == 0:
            print(self.input(1))
        elif not self.active:
            print(self.input(0))


import logging


class Log_Node(DualNodeBase):
    title = 'Log'
    init_inputs = [
        NodeInputBP('exec'),
        NodeInputBP('data', label='msg'),
    ]
    init_outputs = [
        NodeOutputBP('exec'),
    ]
    main_widget_class = widgets.LogNode_MainWidget
    main_widget_pos = 'below ports'
    color = '#5d95de'

    def __init__(self, params):
        super().__init__(params, active=True)

        self.logger = self.new_logger('Log Node')

        self.targets = {
            **self.script.logs_manager.default_loggers,
            'own': self.logger,
        }
        self.target = 'global'

    def update_event(self, input_called=-1):
        if self.active and input_called == 0:
            i = 1
        elif not self.active:
            i = 0
        else:
            return

        msg = self.input(i)

        self.targets[self.target].log(logging.INFO, msg=msg)

    def get_state(self) -> dict:
        return {
            **super().get_state(),
            'target': self.target,
        }

    def set_state(self, data: dict):
        super().set_state(data)
        self.target = data['target']
        if self.session.gui and self.main_widget():
            self.main_widget().set_target(self.target)


class Clock_Node(NodeBase):
    title = 'clock'
    init_inputs = [
        NodeInputBP(dtype=dtypes.Float(default=0.1), label='delay'),
        NodeInputBP(dtype=dtypes.Integer(default=-1, bounds=(-1, 1000)), label='iterations'),
    ]
    init_outputs = [
        NodeOutputBP('exec')
    ]
    color = '#5d95de'
    main_widget_class = widgets.ClockNode_MainWidget
    main_widget_pos = 'below ports'

    def __init__(self, params):
        super().__init__(params)

        self.special_actions['start'] = {'method': self.start}
        self.special_actions['stop'] = {'method': self.stop}

        if self.session.gui:

            from qtpy.QtCore import QTimer
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.timeouted)
            self.iteration = 0


    def timeouted(self):
        self.exec_output(0)
        self.iteration += 1
        if -1 < self.input(1) <= self.iteration:
            self.stop()

    def start(self):
        if self.session.gui:
            self.timer.setInterval(self.input(0)*1000)
            self.timer.start()
        else:
            import time
            for i in range(self.input(1)):
                self.exec_output(0)
                time.sleep(self.input(0))

    def stop(self):
        if self.session.gui:
            self.timer.stop()

    def toggle(self):
        # triggered from main widget
        if self.session.gui:
            if self.timer.isActive():
                self.stop()
            else:
                self.start()

    def update_event(self, input_called=-1):
        if self.session.gui:
            self.timer.setInterval(self.input(0)*1000)

    def remove_event(self):
        self.stop()


class Slider_Node(NodeBase):
    title = 'slider'
    init_inputs = [
        NodeInputBP(dtype=dtypes.Integer(default=1), label='scl'),
        NodeInputBP(dtype=dtypes.Boolean(default=False), label='round'),
    ]
    init_outputs = [
        NodeOutputBP(),
    ]
    main_widget_class = widgets.SliderNode_MainWidget
    main_widget_pos = 'below ports'

    def __init__(self, params):
        super().__init__(params)

        self.val = 0

    def place_event(self):
        self.update()

    def update_event(self, input_called=-1):

        v = self.input(0) * self.val
        if self.input(1):
            v = round(v)

        self.set_output_val(0, v)

    def get_state(self) -> dict:
        return {
            'val': self.val,
        }

    def set_state(self, data: dict):
        self.val = data['val']


class Code_Node(NodeBase):
    title = 'code'
    init_inputs = [

    ]
    init_outputs = [

    ]
    main_widget_class = widgets.CodeNode_MainWidget
    main_widget_pos = 'between ports'

    def __init__(self, params):
        super().__init__(params)

        self.special_actions['add input'] = {'method': self.add_inp}
        self.special_actions['add output'] = {'method': self.add_out}

        self.num_inputs = 0
        self.num_outputs = 0
        self.code = None

    def place_event(self):
        pass

    def add_inp(self):
        self.create_input()

        index = self.num_inputs
        self.special_actions[f'remove input {index}'] = {
            'method': self.remove_inp,
            'data': index
        }

        self.num_inputs += 1

    def remove_inp(self, index):
        self.delete_input(index)
        self.num_inputs -= 1
        del self.special_actions[f'remove input {self.num_inputs}']

    def add_out(self):
        self.create_output()

        index = self.num_outputs
        self.special_actions[f'remove output {index}'] = {
            'method': self.remove_out,
            'data': index
        }

        self.num_outputs += 1

    def remove_out(self, index):
        self.delete_output(index)
        self.num_outputs -= 1
        del self.special_actions[f'remove output {self.num_outputs}']

    def update_event(self, input_called=-1):
        exec(self.code)

    def get_state(self) -> dict:
        return {
            'num inputs': self.num_inputs,
            'num outputs': self.num_outputs,
            'code': self.code,
        }

    def set_state(self, data: dict):
        self.num_inputs = data['num inputs']
        self.num_outputs = data['num outputs']
        self.code = data['code']


class Eval_Node(NodeBase):
    title = 'eval'
    init_inputs = [
        # NodeInputBP(),
    ]
    init_outputs = [
        NodeOutputBP(),
    ]
    main_widget_class = widgets.EvalNode_MainWidget
    main_widget_pos = 'between ports'

    def __init__(self, params):
        super().__init__(params)

        self.special_actions['add input'] = {'method': self.add_param_input}

        self.number_param_inputs = 0
        self.expression_code = None

    def place_event(self):
        if self.number_param_inputs == 0:
            self.add_param_input()

    def add_param_input(self):
        self.create_input()

        index = self.number_param_inputs
        self.special_actions[f'remove input {index}'] = {
            'method': self.remove_param_input,
            'data': index
        }

        self.number_param_inputs += 1

    def remove_param_input(self, index):
        self.delete_input(index)
        self.number_param_inputs -= 1
        del self.special_actions[f'remove input {self.number_param_inputs}']

    def update_event(self, input_called=-1):
        inp = [self.input(i) for i in range(self.number_param_inputs)]
        self.set_output_val(0, eval(self.expression_code))

    def get_state(self) -> dict:
        return {
            'num param inputs': self.number_param_inputs,
            'expression code': self.expression_code,
        }

    def set_state(self, data: dict):
        self.number_param_inputs = data['num param inputs']
        self.expression_code = data['expression code']


# -------------------------------------------


nodes = [
    Button_Node,
    Print_Node,
    Log_Node,
    Clock_Node,
    Slider_Node,
    Code_Node,
    Eval_Node,
]