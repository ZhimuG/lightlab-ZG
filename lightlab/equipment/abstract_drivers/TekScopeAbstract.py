import numpy as np

from lightlab import logger
from lightlab.util.data import Waveform, FunctionBundle

# Circular dependency. Instead it is imported within __init__.
# Python resolves this but Sphinx does not!
# from lightlab.equipment.lab_instruments.visa_drivers import VISAInstrumentDriver

from .configurable import Configurable



class TekScopeAbstract(Configurable):
    '''
        General class for several Tektronix scopes, including

            * `DPO 4034 <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`_
            * `DPO 4032 <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`_
            * `DSA 8300 <http://www.tek.com/download?n=975655&f=190886&u=http%3A%2F%2Fdownload.tek.com%2Fsecure%2FDifferential-Channel-Alignment-Application-Online-Help.pdf%3Fnvb%3D20170404035703%26amp%3Bnva%3D20170404041203%26amp%3Btoken%3D0ccdfecc3859114d89c36>`_
            * `TDS 6154C <http://www.tek.com/sites/tek.com/files/media/media/resources/55W_14873_9.pdf>`_

        The main method is :py:meth:`acquire`, which takes and returns a :py:class:`~Waveform`.

        Todo:
            These behave differently. Be more explicit about sample mode::

                timebaseConfig(avgCnt=1)
                acquire([1])

                acquire([1], avgCnt=1)

            Does DPO support sample mode at all?
    '''
    # This should be overloaded by the particular driver
    totalChans = None

    __recLenParam = None
    __clearBeforeAcquire = None
    __measurementSourceParam = None
    __runModeParam = None
    __runModeSingleShot = None

    def __init__(self, *args, **kwargs):
        # These lines require a circular import dependency, so it is done within the method
        from lightlab.equipment.lab_instruments.visa_drivers import VISAInstrumentDriver
        if not isinstance(self, VISAInstrumentDriver):
            raise TypeError(str(type(self)) + ' is abstract and cannot be initialized')
        super().__init__(*args, **kwargs)

    def startup(self):
        # Make sure sampling and data transferring are in a consistent state
        initNpts = self.getConfigParam(self.__recLenParam)
        self.acquire(nPts=initNpts)

    def timebaseConfig(self, avgCnt=None, duration=None, position=None, nPts=None):
        ''' Timebase and acquisition configure

            Args:
                avgCnt (int): averaging done by the scope
                duration (float): time, in seconds, for data to be acquired
                position (float): trigger delay
                nPts (int): number of samples taken

            Returns:
                (dict) The present values of all settings above
        '''
        if avgCnt is not None and avgCnt > 1:
            self.setConfigParam('ACQUIRE:NUMAVG', avgCnt, forceHardware=True)
        if duration is not None:
            self.setConfigParam('HORIZONTAL:MAIN:SCALE', duration/10)
        if position is not None:
            self.setConfigParam('HORIZONTAL:MAIN:POSITION', position)
        if nPts is not None:
            self.setConfigParam(self.__recLenParam, nPts)
            self.setConfigParam('DATA:START', 1)
            self.setConfigParam('DATA:STOP', nPts)

        presentSettings = dict()
        presentSettings['avgCnt'] = self.getConfigParam('ACQUIRE:NUMAVG')
        presentSettings['duration'] = self.getConfigParam('HORIZONTAL:MAIN:SCALE')
        presentSettings['position'] = self.getConfigParam('HORIZONTAL:MAIN:POSITION')
        presentSettings['nPts'] = self.getConfigParam(self.__recLenParam)
        return presentSettings

    def acquire(self, chans=None, **kwargs):
        ''' Get waveforms from the scope.

            If chans is None, it won't actually trigger, but it will configure.

            If unspecified, the kwargs will be derived from the previous state of the scope.
            This is useful if you want to play with it in lab while working with this code too.

            Args:
                chans (list): which channels to record at the same time and return

            Returns:
                list[Waveform]: recorded signals
        '''
        self.timebaseConfig(**kwargs)
        if chans is None:
            return

        for c in chans:
            if c > self.totalChans:
                raise Exception('Received channel: ' + str(c) +
                    '. Max channels of this scope is ' + str(self.totalChans))

        # Channel select
        for ich in range(1, 1 + self.totalChans):
            thisState = 1 if ich in chans else 0
            self.setConfigParam('SELECT:CH' + str(ich), thisState)

        isSampling = kwargs.get(avgCnt, 0) == 1
        self.__setupSingleShot(isSampling)
        self.__triggerAcquire()
        wfms = [None] * len(chans)
        for i, c in enumerate(chans):
            vRaw = self.__transferData(c)
            t, v = self.__scaleData(vRaw)
            wfms[i] = Waveform(t, v)

        return wfms

    def __setupSingleShot(self, isSampling, forcing=False):
        ''' Set up a single shot acquisition.

                Not running continuous, and
                acquire mode set SAMPLE/AVERAGE

            Subclasses usually have additional settings to set here.

            Args:
                isSampling (bool): is it in sampling (True) or averaging (False) mode
                forcing (bool): if False, trusts that no manual changes were made, except to run continuous/RUNSTOP

            Todo:
                Missing DPO trigger source setting.
                Should we force it when averaging?
                Probably not because it could be CH1, CH2, AUX.
        '''
        self.run(False)
        self.setConfigParam('ACQUIRE:MODE',
                            'SAMPLE' if isSampling else 'AVERAGE',
                            forceHardware=forcing)

    def __triggerAcquire(self):
        ''' Sends a signal to the scope to wait for a trigger event. Waits until acquisition completes
        '''
        if self.__clearBeforeAcquire:
            self.write('ACQUIRE:DATA:CLEAR') # clear out average history
        self.write('ACQUIRE:STATE 1') # activate the trigger listener
        self.wait(30000) # Bus and entire program stall until acquisition completes. Maximum of 30 seconds

    def __transferData(self, chan):
        ''' Returns the raw data pulled from the scope as time (seconds) and voltage (Volts)
            Args:
                chan (int): one channel at a time

            Returns:
                :py:mod:`data.Waveform`: a time, voltage paired signal

            Todo:
                Make this binary transfer to go even faster
        '''
        chStr = 'CH' + str(chan)
        self.setConfigParam('DATA:ENCDG', 'ASCII')
        self.setConfigParam('DATA:SOURCE', chStr)
        self.open(self)
        try:
            voltRaw = self.mbSession.query_ascii_values('CURV?')
        except pyvisa.VisaIOError as err:
            logger.error('Problem during query_ascii_values(\'CURV?\')')
            try:
                self.close(self)
            except:
                logger.error('Failed to close!', self.address)
                pass
            raise err
        self.close(self)
        return voltRaw

    def __scaleData(self, voltRaw):
        ''' Scale to second and voltage units.

            DSA and DPO are very annoying about treating ymult and yscale differently.
            TDS uses ymult not yscale

            Args:
                voltRaw (ndarray): what is returned from ``__transferData``

            Returns:
                (ndarray): time in seconds, centered at t=0 regardless of timebase position
                (ndarray): voltage in volts
        '''
        get = lambda param: float(self.getConfigParam('WFMOUTPRE:' + param, forceHardware=True))
        voltage = (np.array(voltRaw) - get('YZERO')) \
                  * get(self.yScaleParam) \
                  + get('YOFF')

        timeDivision = float(self.getConfigParam('HORIZONTAL:MAIN:SCALE'))
        time = np.linspace(-1, 1, len(voltage))/2 *  timeDivision * 10

        return time, voltage

    def wfmDb(self, chan, nWfms, untriggered=False):
        ''' Transfers a bundle of waveforms representing a signal database. Sample mode only.

            Configuration such as position, duration are unchanged, so use an acquire(None, ...) call to set them up

            Args:
                chan (int): currently this only works with one channel at a time
                nWfms (int): how many waveforms to acquire through sampling
                untriggered (bool): if false, temporarily puts scope in free run mode

            Returns:
                (FunctionBundle(Waveform)): all waveforms acquired
        '''
        bundle = FunctionBundle()
        with self.tempConfig('TRIGGER:SOURCE',
                'FREERUN' if untriggered else 'EXTDIRECT'):
            for _ in range(nWfms):
                bundle.addDim(self.acquire([chan], avgCnt=1)[0]) # avgCnt=1 sets it to sample mode
        return bundle

    def run(self, continuousRun=True):
        ''' Sets the scope to continuous run mode, so you can look at it in lab,
            or to single-shot mode, so that data can be acquired

            Args:
                continuousRun (bool)
        '''
        self.setConfigParam(self.__runModeParam,
                            'RUNSTOP' if continuousRun else self.__runModeSingleShot,
                            forceHardware=True)
        if continuousRun:
            self.setConfigParam('ACQUIRE:STATE', 1, forceHardware=True)

    def setMeasurement(measIndex, chan, measType):
        '''
            Args:
                measIndex (int): used to refer to this measurement itself. 1-indexed
                chan (int): the channel source of the measurement.
                measType (str): can be 'PK2PK', 'MEAN', etc.
        '''
        if measIndex == 0:
            raise ValueError('measIndex is 1-indexed')
        measSubmenu = 'MEASUREMENT:MEAS' + str(measIndex) + ':'
        self.setConfigParam(measSubmenu + self.__measurementSourceParam, chStr)
        self.setConfigParam(measSubmenu + 'TYPE', measType.upper())
        self.setConfigParam(measSubmenu + 'STATE', 1)

    def measure(measIndex):
        '''
            Args:
                measIndex (int): used to refer to this measurement itself. 1-indexed

            Returns:
                (float)
        '''
        measSubmenu = 'MEASUREMENT:MEAS' + str(measIndex) + ':'
        return float(self.query(measSubmenu + 'VALUE?'))

    def autoAdjust(self, chans):
        ''' Adjusts offsets and scaling so that waveforms are not clipped '''
        # Save the current measurement status. They will be restored at the end.
        self.saveConfig(dest='+autoAdjTemp', subgroup='MEASUREMENT')

        for ch in chans:
            chStr = 'CH' + str(ch)

            # Set up measurements
            self.setMeasurement(1, ch, 'pk2pk')
            self.setMeasurement(2, ch, 'mean')

            for iTrial in range(100):
                # Acquire new data
                self.acquire(chans=[ch], avgCnt=1)

                # Put measurements into measResult
                pk2pk = self.measure(1)
                mean = self.measure(2)

                span = float(self.getConfigParam(chStr + ':SCALE'))
                offs = float(self.getConfigParam(chStr + ':OFFSET'))

                # Check if scale is correct within the tolerance
                newSpan = None
                newOffs = None
                if pk2pk < 0.7 * span:
                    newSpan = pk2pk / 0.75
                elif pk2pk > 0.8 * span:
                    newSpan = 2 * span
                if newSpan < 0.1 or newSpan > 100:
                    raise Exception('Scope channel ' + chStr + ' could not be adjusted.')

                # Check if offset is correct within the tolerance
                if abs(mean) > 0.05 * span:
                    newOffs = offs - mean

                # If we didn't set the new variables, then we're good to go
                if newSpan is not None and newOffs is not None:
                    break

                # Adjust settings
                self.setConfigParam(chStr + ':SCALE', newSpan / 10)
                self.setConfigParam(chStr + ':OFFSET', newOffs)

        # Recover the measurement setup from before adjustment
        self.loadConfig(source='+autoAdjTemp', subgroup='MEASUREMENT')
        self.config.pop('autoAdjTemp')

