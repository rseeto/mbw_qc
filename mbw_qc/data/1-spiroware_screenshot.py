"""Script to obtain screenshots from Spiroware"""

import time
import os
import os.path as path
import re
from collections import Counter
import pandas as pd
import pyautogui


def start_spiroware():
    """Start Spiroware software using pyautogui

    Opens Spiroware software and logs in. Assumes the Spiroware shortcut icon
    is in the bottom left hand corner of the desktop.

    Returns
    -------
    None
    """
    # open program
    pyautogui.doubleClick(x=35, y=935)
    time.sleep(1)

    # make sure the login screen is zoomed in properly
    pyautogui.doubleClick(x=1810, y=1024)

    # User
    pyautogui.doubleClick(x=830, y=635)
    pyautogui.write('admin')
    time.sleep(0.25)

    # Password
    pyautogui.doubleClick(x=1020, y=635)
    pyautogui.write('admin')
    time.sleep(0.25)

    # Click login
    pyautogui.click(x=1150, y=635)
    time.sleep(3)


def close_spiroware():
    """Close Spiroware software using pyautogui

    Closes Spiroware software by clicking the 'x' in the top right hand corner.
    Assumes Spiroware software is in 'full screen' mode.

    Returns
    -------
    None
    """
    # open program
    pyautogui.doubleClick(x=1895, y=10)
    time.sleep(0.5)


def from_select_to_history(patient_number):
    """Move from 'Select' screen to 'History' screen in Spiroware

    Move from the 'Select' screen to the 'History' screen by entering
    patient number into Spiroware

    Parameters
    ----------
    patient_number : str
        Patient number to be entered into Spiroware

    Returns
    -------
    None
    """
    # move to 'x' in 'Filter' field; clears value if necessary
    pyautogui.doubleClick(x=235, y=80)
    # enter patient number into search field
    pyautogui.write(patient_number)
    # click associated number in 'Patient List'
    pyautogui.doubleClick(x=40, y=144)
    time.sleep(2)


def from_history_to_mbw():
    """Move from 'History' screen to 'MBW' screen in Spiroware

    Returns
    -------
    None
    """
    # MBW test may have a grey or white background depending on when it was
    # completed in relation to other MBW tests
    try:
        # releavnt MBW test will be first on list; coloured grey
        mbw = pyautogui.center(
            pyautogui.locateOnScreen(
                path.abspath(path.join(
                    path.dirname(__file__),
                    'assets/patient_history_lci_grey.png'
                )),
                confidence=0.85
            )
        )
    except Exception as e:
        # relevant MBW test will not be first on list; coloured white
        mbw = pyautogui.center(
            pyautogui.locateOnScreen(
                path.abspath(path.join(
                    path.dirname(__file__),
                    'assets/patient_history_lci_white.png'
                )),
                confidence=0.85
            )
        )
    pyautogui.moveTo(x=mbw.x, y=mbw.y)
    time.sleep(0.25)
    pyautogui.doubleClick(x=mbw.x, y=mbw.y)
    time.sleep(25)


def click_trial_num(trial_num):
    """Click the trial number of interest

    Determines where to click on the Spiroware software based on the trial
    number, with lower trial numbers higher on the screen and higher trial
    numbers lower on the screen.

    Parameters
    ----------
    trial_num : int
        Trial number of interest

    Returns
    -------
    None
    """
    # maximize 'Trials' window
    trial_window_border = pyautogui.center(
        pyautogui.locateOnScreen(
            path.abspath(path.join(
                path.dirname(__file__), 'assets/trial_border.png'
            )),
            confidence=0.7
        )
    )
    pyautogui.moveTo(x=trial_window_border.x, y=(trial_window_border.y - 20))
    time.sleep(0.5)
    pyautogui.dragTo(
        x=trial_window_border.x, y=945,
        duration=3, button='left', tween=quick_in_wait
    )

    # click appropriate trial number
    # expected y value of trial 1 is 320
    # average number of pixels between trials is 21
    pyautogui.doubleClick(x=665, y=(330 + (trial_num - 1) * 21))

    time.sleep(2)


def check_range(num):
    """Raises ValueError if the argument is not between 0.0 and 1.0.

    Notes
    -----
    Modified from pytweening
    https://github.com/asweigart/pytweening/blob/master/pytweening/__init__.py

    Raises
    ------
    ValueError
        If the argument is not between 0.0 and 1.0 inclusive

    """
    if not 0.0 <= num <= 1.0:
        raise ValueError('Argument must be between 0.0 and 1.0.')


def quick_in_wait(num):
    """A custom tween function that quickly goes to the end then waits.

    Notes
    -----
    Modified from pytweening
    https://github.com/asweigart/pytweening/blob/master/pytweening/__init__.py

    Parameters
    ----------
    n: float
        The time progress, starting at 0.0 and ending at 1.0.

    Returns
    -------
    float
        The line progress, starting at 0.0 and ending at 1.0.
    """
    check_range(num)
    if num < 0.1:
        return num/0.1
    else:
        return 1.0


def format_mbw_screen():
    """Formats the MBW screen

    Clicks 'Reset' and closes the flow and CO2 figure to ensure consistency
    while running.

    Returns
    -------
    None
    """
    # click 'Reset'
    pyautogui.click(x=1663, y=88)
    time.sleep(0.5)
    pyautogui.click(x=1723, y=189)

    # close flow and CO2% figures
    pyautogui.moveTo(x=565, y=500)
    pyautogui.dragTo(x=1, y=500, duration=3, button='left', tween=quick_in_wait)
    time.sleep(2)


def take_flow_screenshots(save_path, patient_num, trial_num):
    """Take a 'Flow' screenshot

    Parameters
    ----------
    save_path : str
        Path where the screenshot will be saved
    patient_num : str
        Patient number to be incorporated into file name
    trial_num : int
        Trial number to be incorporated into file name. Parameter will be
        converted to str when passed to take_screenshot()

    Returns
    -------
    None
    """
    # maximize figure
    pyautogui.moveTo(x=825, y=535)
    pyautogui.dragTo(x=825, y=970, duration=3, button='left', tween=quick_in_wait)
    time.sleep(2)

    # deactivate volume figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=105)
    time.sleep(1)
    pyautogui.click(x=1600, y=118)

    # take screenshot
    take_screenshot(save_path, patient_num, trial_num, 'flow')


def take_volume_screenshots(save_path, patient_num, trial_num):
    """Takes a 'Volume' screenshot

    Notes
    -----
    Assumed to proceed after take_flow_screenshot()

    Parameters
    ----------
    save_path : str
        Path where the screenshot will be saved
    patient_num : str
        Patient number to be incorporated into file name
    trial_num : int
        Trial number to be incorporated into file name. Parameter will be
        converted to str when passed to take_screenshot()

    Returns
    -------
    None
    """
    # activate volume figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=105)
    time.sleep(1)
    pyautogui.click(x=1600, y=118)

    # deactivate volume figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=105)
    time.sleep(1)
    pyautogui.click(x=1600, y=105)

    # take screenshot
    take_screenshot(save_path, patient_num, trial_num, 'volume')


def take_n2_screenshots(save_path, patient_num, trial_num):
    """Take 'N2' screenshot

    Notes
    -----
    Assumed to proceed after take_volume_screenshot()

    Parameters
    ----------
    save_path : str
        Path where the screenshot will be saved
    patient_num : str
        Patient number to be incorporated into file name
    trial_num : int
        Trial number to be incorporated into file name. Parameter will be
        converted to str when passed to take_screenshot()

    Returns
    -------
    None
    """
    # maximize figure
    pyautogui.moveTo(x=825, y=960)
    pyautogui.dragTo(x=825, y=90, duration=3, button='left', tween=quick_in_wait)
    time.sleep(2)

    # take screenshot
    take_screenshot(save_path, patient_num, trial_num, 'n2')


def take_o2_screenshots(save_path, patient_num, trial_num):
    """Take 'O2' screenshot

    Notes
    -----
    Assumed to proceed after take_n2_screenshot()

    Parameters
    ----------
    save_path : str
        Path where the screenshot will be saved
    patient_num : str
        Patient number to be incorporated into file name
    trial_num : int
        Trial number to be incorporated into file name. Parameter will be
        converted to str when passed to take_screenshot()

    Returns
    -------
    None
    """
    # activate O2 figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=132)

    # maximize figure
    pyautogui.moveTo(x=825, y=960)
    pyautogui.dragTo(x=825, y=90, duration=3, button='left', tween=quick_in_wait)
    time.sleep(2)

    # take screenshot
    take_screenshot(save_path, patient_num, trial_num, 'o2')


def take_co2_screenshots(save_path, patient_num, trial_num):
    """Take 'CO2' screenshot

    Notes
    -----
    Assumed to proceed after take_n2_screenshot()

    Parameters
    ----------
    save_path : str
        Path where the screenshot will be saved
    patient_num : str
        Patient number to be incorporated into file name
    trial_num : int
        Trial number to be incorporated into file name. Parameter will be
        converted to str when passed to take_screenshot()

    Returns
    -------
    None
    """
    # deactivate O2 figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=132)

    # activate CO2 figure
    pyautogui.click(x=1663, y=88)
    time.sleep(1)
    pyautogui.click(x=1723, y=150)

    # maximize figure
    pyautogui.moveTo(x=825, y=960)
    pyautogui.dragTo(x=825, y=90, duration=3, button='left', tween=quick_in_wait)
    time.sleep(2)

    # take screenshot
    take_screenshot(save_path, patient_num, trial_num, 'co2')


def press_back():
    """Press the back button

    Returns
    -------
    None
    """
    pyautogui.click(x=1800, y=995)
    time.sleep(2)


def take_screenshot(save_path, patient_num, trial_num, shot_type):
    """Take screenshot

    Parameters
    ----------
    save_path : str
        Root save path
    patient_num : str
        Patient number associated with screenshot
    trial_num : int
        Trial number associated with screenshot
    shot_type : str
        Type of screenshot

    Returns
    -------
    None
    """
    # take screenshot
    zoom_out()
    pyautogui.screenshot(
        '{}/{}_trial_{}_{}.png'.format(
            save_path, patient_num, str(trial_num), shot_type
        )
    )
    zoom_in()


def zoom_in():
    """Zooms in on figure

    Returns
    -------
    None
    """
    pyautogui.moveTo(x=1894, y=1024)
    pyautogui.dragTo(
        x=1810, y=1024, duration=3, button='left', tween=quick_in_wait
    )
    time.sleep(1)


def zoom_out():
    """Zooms out on figure

    Returns
    -------
    None
    """
    pyautogui.moveTo(x=1810, y=1024)
    pyautogui.dragTo(
        x=1912, y=1024, duration=3, button='left', tween=quick_in_wait
    )
    time.sleep(1)


def main():
    save_path = path.abspath(path.join(
        __file__ , '../../../data/raw/spiroware_screenshots/'
    ))
    spx_filename_saved = [
        re.sub('_(o2|co2|n2|flow|volume).png', '', fname)
        for fname in os.listdir(save_path)
    ]
    # determine which files are in the save path and keep those with 5
    # files (i.e. o2, co2, n2, flow, volume); those without 5 files (incomplete
    # data) will have their data processed
    counts = Counter(spx_filename_saved)
    spx_filename_saved = []
    for key, val in counts.items():
        if val == 5:
            spx_filename_saved.append(key)

    pat_num_trials = pd.read_csv(path.abspath(path.join(
        __file__ , '../../../data/external/track_redcap_qc-16JUL2021.csv'
    )))
    # alternatively may need to open the LONGITUDINAL data
    # pat_num_trials = pd.read_csv(path.abspath(path.join(
    #     __file__ , '../../../data/external/longitudinal_redcap_qc-20AUG2021.csv'
    # )))

    if 'spx_filename' not in pat_num_trials.columns.values:
        pat_num_trials['spx_filename'] = pat_num_trials['id'].astype(str)

    # remove spx_filenames already completed
    pat_num_trials['spx_filename_trial'] = (
        '{}_trial_{}'.format(
            pat_num_trials['spx_filename'].astype(str),
            pat_num_trials['trial'].astype(str)
        )
    )
    pat_num_trials = pat_num_trials[
        ~pat_num_trials['spx_filename_trial'].isin(spx_filename_saved)
    ]

    # get the max number of trials; assumes trials are consecutive
    pat_num_trials_dict = (
        pat_num_trials
        .groupby('spx_filename', as_index=True)
        .agg({"trial": "max"})
    )
    pat_num_trials_dict = pat_num_trials_dict.to_dict()['trial']

    # minimize code window
    pyautogui.click(x=1803, y=19)

    for patient_num, total_trials in pat_num_trials_dict.items():

        while True:
            try:
                start_spiroware()

                from_select_to_history(patient_num)

                for trial_num in range(1, (total_trials + 1)):
                    from_history_to_mbw()
                    click_trial_num(trial_num)
                    format_mbw_screen()

                    take_flow_screenshots(save_path, patient_num, trial_num)
                    take_volume_screenshots(save_path, patient_num, trial_num)
                    take_n2_screenshots(save_path, patient_num, trial_num)
                    take_o2_screenshots(save_path, patient_num, trial_num)
                    take_co2_screenshots(save_path, patient_num, trial_num)

                    press_back()

                close_spiroware()
                break
            except Exception as e:
                close_spiroware()


if __name__ == "__main__":
    main()
