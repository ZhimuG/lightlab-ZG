from lightlab.equipment.abstract_drivers import kf
from lightlab.util.data import Waveform

import numpy as np
import matplotlib.pyplot as plt

class Agilent_54846B_Oscope (kf.VisaManager):

    def __init__(self, name='Infiniium Oscilloscope', address=None, **kwargs):
        self.FlexDCA = kf.VisaManager(address=address, scpi_echo=False)

    def __del__(self):
        # self.FlexDCA.write(':SYSTem:GTLocal')
        self.FlexDCA.close()

    def configure_Oscope_pattern(self, channel, scale=None):
        """ Installs a simulated module and prepares FlexDCA for
        measurements.
        """
        self.FlexDCA.query('*OPC?')
        self.FlexDCA.write('*RST')
        self.FlexDCA.write('*CLS')
        self.FlexDCA.write(':SYSTem:HEADer ON')
        self.FlexDCA.write(':TIMebase:REFerence CENTer;RANGe 5e-3;POSition 20e-6')
        self.FlexDCA.write(f':CHANnel{channel}:RANGe 1.6;OFFSet -400e-3')
        self.FlexDCA.write(f':TRIGger:EDGE:SOURce CHANnel{channel};SLOPe POSitive')
        self.FlexDCA.write(f':TRIGger:LEVel CHANnel{channel},-0.40')
        self.FlexDCA.write(':ACQuire:MODE RTIMe;AVERage OFF;POINts 4096')
        self.FlexDCA.write(':AUTOSCALE;*OPC?')
        self.FlexDCA.write(':STOP')
        # self.FlexDCA.write(':ACQuire:RUN')
        # self.FlexDCA.query(':SYSTem:MODE OSCilloscope;*OPC?')
        # self.FlexDCA.write(':TRIGger:PLOCk ON')
        # self.FlexDCA.write(':ACQuire:EPATtern ON')
        # while True:
            # if self.FlexDCA.query(':WAVeform:PATTern:COMPlete?'):
                # break
        # if scale is None:
            # self.FlexDCA.query(':SYSTem:AUToscale;*OPC?')
        # else:
            # self.magnifier(scale[0], scale[1], channel)
            # self.FlexDCA.query('*OPC?')
        # self.FlexDCA.write(':TIMebase:UNIT UINTerval')
        # pattern_length = self.FlexDCA.query(':TRIGger:PLENgth?')
        # self.FlexDCA.write(':TIMebase:UIRange ' + pattern_length)

    def get_pattern_info(self, channel):
        message = ':SYSTem:SETup?'
        # set_up = self.FlexDCA.query(':SYSTem:SETup?')
        set_up = self.FlexDCA.query_binary_values(message, datatype='p', container=list, is_big_endian=True, header_fmt='ieee')
        return set_up
        # print('Get pattern scaling information.', flush=True)
        # values = {'p_length': '',
                  # 'p_points': '',
                  # 'xmin': '',
                  # 'xmax': '',
                  # 'ymin': '',
                  # 'ymax': '',
                  # 'xscale': '',
                  # 'yscale': ''}
        # self.FlexDCA.write(':WAVeform:SOURce CHANnel' + channel)
        # values['p_length'] = self.FlexDCA.query(':WAVeform:PATTern:BITS?')
        # values['p_points'] = int(self.FlexDCA.query(':WAVeform:XYFORmat:POINts?'))
        # values['xmin'] = self.FlexDCA.query(':TIMebase:XLEFt?')
        # values['xmax'] = self.FlexDCA.query(':TIMebase:XRIGht?')
        # values['ymin'] = self.FlexDCA.query(':CHANnel' + channel + ':YBOTTom?')
        # values['ymax'] = self.FlexDCA.query(':CHANnel' + channel + ':YTOP?')
        # values['xscale'] = self.FlexDCA.query(':TIMebase:SCALe?')
        # values['yscale'] = self.FlexDCA.query(':CHANnel' + channel + ':YSCale?')
        # print('-' * 30)
        # print('X-scale maximum: ' + kf.eng_notation(values['xmax'], '1.00') + 's')
        # print('X-scale minimum: ' + kf.eng_notation(values['xmin'], '1.00') + 's')
        # print('Y-scale maximum: ' + kf.eng_notation(values['ymax'], '1.00') + 'V')
        # print('Y-scale minimum: ' + kf.eng_notation(values['ymin'], '1.00') + 'V')
        # print('Pattern length: ' + values['p_length'] + ' bits')
        # print('Data points: ' + str(values['p_points']))
        # print('-' * 30)
        # return values
        
    def get_waveform_data(self, channel):
        self.FlexDCA.write(':SYSTem:HEADer OFF')
        self.FlexDCA.write(f':WAVeform:SOURce CHANnel{channel}')
        self.FlexDCA.write(':WAVeform:FORMat WORD')
        # self.FlexDCA.query(':WAVeform:DATA?')
        message = ':WAVeform:DATA?'
        data = self.FlexDCA.query_binary_values(message, datatype='h', container=list, is_big_endian=True, header_fmt='ieee')
        return data

    # def get_waveform_x_data(self):
        # """ Reads x data as floats. Using pyvisa's read_raw() method requires
        # that :WAVeform:XYFORmat:FLOat:XDATa? query be sent using the write()
        # method followed by separate read_raw().
        # """
        # print('Get pattern waveform X data.', flush=True)
        # x_data = []  # Python 3 raw byte string
        # endiansetting = self.FlexDCA.query(':SYSTem:BORDER?')  # get current byte order
        # self.FlexDCA.write(':SYSTem:BORDER LENDian')  # set little endian byte order
        # message = ':WAVeform:XYFORmat:FLOat:XDATa?'
        # x_data = self.FlexDCA.query_binary_values(message,
                                                  # datatype='f',
                                                  # container=list,
                                                  # is_big_endian=False,
                                                  # header_fmt='ieee')
        # self.FlexDCA.write(':SYSTem:BORDER ' + endiansetting)
        # # scale data
        # n = 0
        # while n < len(x_data):
            # x_data[n] *= 1E9  # data in mV
            # n += 1
        # return x_data
        
    # def get_waveform_y_data(self):
        # """ Reads y data as floats. Using pyvisa's read_raw() method requires
        # that :WAVeform:XYFORmat:FLOat:XDATa? query be sent using the write()
        # method followed by separate read_raw().
        # """
        # print('Get pattern waveform Y data.', flush=True)
        # y_data = []
        # endiansetting = self.FlexDCA.query(':SYSTem:BORDER?')  # get current byte order
        # self.FlexDCA.write(':SYSTem:BORDER LENDian')  # set little endian byte order
        # message = ':WAVeform:XYFORmat:FLOat:YDATa?'
        # y_data = self.FlexDCA.query_binary_values(message,
                                                  # datatype='f',
                                                  # container=list,
                                                  # is_big_endian=False,
                                                  # header_fmt='ieee')
        # self.FlexDCA.write(':SYSTem:BORDER ' + endiansetting)
        # # scale data
        # n = 0
        # while n < len(y_data):
            # y_data[n] *= 1E3  # data in ns
            # n += 1
        # return y_data

    # def magnifier(self, xScale=None, yScale=None, channel=None):
        # if xScale is not None:
            # try:
                # self.FlexDCA.write(':TIMebase:SCALe '+xScale)
            # except Exception as e:
                # print(e)
                # raise e
        # if yScale is not None and channel is not None:
            # try:
                # self.FlexDCA.write(':CHANnel'+str(channel)+'YSCale '+str(yScale))
            # except Exception as e:
                # print(e)
                # raise e
        
    def acquire_pattern(self, channel, scale=None):
        self.configure_Oscope_pattern(channel, scale)
        values = self.get_pattern_info(channel)
        data = self.get_waveform_data(channel)
        self.FlexDCA.write(':RUN')
        # y_data = self.get_waveform_y_data()
        # self.draw_graph_pattern(y_data, x_data, values, channel)
        return data, values