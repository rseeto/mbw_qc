"""Digitize Spiroware screenshot"""

import argparse
import pathlib
import re
import os
import cv2
import pytesseract
import numpy as np
# plotdigitizer is slightly modified from source; no longer checks for gridlines
import plotdigitizer.plotdigitizer

# contains all 'grey' gridlines derived from 202.2_trial_3_co2.png;
# used to determine if an element is a gridline
gray_list = [
    [214, 214, 214], [235, 235, 235], [198, 198, 198], [209, 209, 209],
    [230, 230, 230], [201, 201, 201], [245, 245, 245], [236, 236, 236],
    [206, 206, 206], [195, 195, 195], [244, 244, 244], [247, 247, 247],
    [243, 243, 243], [223, 223, 223], [215, 215, 215], [246, 246, 246],
    [194, 194, 194], [232, 232, 232], [203, 203, 203], [224, 224, 224],
    [196, 196, 196], [220, 220, 220], [211, 211, 211], [221, 221, 221],
    [239, 239, 239], [210, 210, 210], [197, 197, 197], [205, 205, 205],
    [218, 218, 218], [200, 200, 200], [249, 249, 249], [228, 228, 228],
    [248, 248, 248], [207, 207, 207], [199, 199, 199]
]


def crop_screenshot(screenshot, bottom_left_template, top_right_template):
    """Crop Spiroware screenshot

    Parameters
    ----------
    screenshot : numpy.ndarray
        Screenshot to be cropped
    bottom_left_template : numpy.ndarray
        Templated used to find the location of the bottom left corner
    top_right_template : numpy.ndarray
        Templated used to find the location of the top right corner

    Returns
    -------
    numpy.ndarray
        Screenshot that is cropped based on templates

    Reference
    ---------
    https://pyimagesearch.com/2021/03/22/opencv-template-matching-cv2-matchtemplate/
    """

    # convert images to grayscale to speed up processing
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    bottom_left_template_gray = cv2.cvtColor(bottom_left_template, cv2.COLOR_BGR2GRAY)
    top_right_template_gray = cv2.cvtColor(top_right_template, cv2.COLOR_BGR2GRAY)

    # get location info from screenshots
    bottom_left_result = cv2.matchTemplate(
        screenshot_gray, bottom_left_template_gray, cv2.TM_CCOEFF_NORMED
    )
    top_right_result = cv2.matchTemplate(
        screenshot_gray, top_right_template_gray, cv2.TM_CCOEFF_NORMED
    )
    (_, _, _, bottom_left_coor) = cv2.minMaxLoc(bottom_left_result)
    (_, _, _, top_right_coor) = cv2.minMaxLoc(top_right_result)

    # crop using the top left corner of bottom_left_coordinates and
    # bottom right corner of top_right_template
    crop_img = screenshot[
        (top_right_coor[1] + top_right_template.shape[0]):bottom_left_coor[1],
        bottom_left_coor[0]:(top_right_coor[0] + top_right_template.shape[1]),
    ]

    return crop_img


def convert_bw(figure, threshold=180):
    """Convert a colour image to black and white

    Parameters
    ----------
    figure : numpy.ndarray
        Image to be converted
    threshold : int, optional
        Threshold used to determine which elements are black and white,
        by default 180

    Returns
    -------
    numpy.ndarray
        Image converted to black and white
    """
    figure_gray = cv2.cvtColor(figure, cv2.COLOR_BGR2GRAY)
    figure_bw = cv2.threshold(figure_gray, threshold, 255, cv2.THRESH_BINARY)[1]

    return figure_bw


def hor_char_row_ind(figure):
    """Get index associated with the horizontal (x) axis

    The 'figure' parameter should contain a figure with vertical and horizontal
    axis text. This function finds the index associated with the white gap.
    For example, there should be a gap of all white pixels between the black
    pixels of the horizontal axis text and the black pixels associated with the
    numbers of the x-axis tick marks. This function aims to find the index
    associated with the gap of white pixels. The results of this function can
    then be used to trim the axis from the figure.

    Parameters
    ----------
    figure : numpy.ndarray
        Image of interest

    Returns
    -------
    int
        Index of white gap
    """
    figure = convert_bw(figure, 150)
    is_white_line = True
    # starting from the bottom of the image, horizontally interate over pixels
    # stop when the horizontal line contains a non-white pixel
    # will use the x_coor (horizontal line) in next step
    for x_coor in range(figure.shape[0] - 1, 0, -1):
        for y_coor in range(figure.shape[1] - 1):
            if figure[x_coor, y_coor] != 255:
                is_white_line = False
                break
        if not is_white_line:
            break
    # starting from the previous step, horizontally interate over pixels
    # stop when the horizontal line contains only white pixels
    for x_coor_2 in range(x_coor, 0, -1):
        for y_coor_2 in range(figure.shape[1] - 1):
            is_white_line = True
            if figure[x_coor_2, y_coor_2] != 255:
                is_white_line = False
                break
        if is_white_line:
            break

    return x_coor_2 - 1


def ver_char_row_ind(figure):
    """Get index associated with the vertical (y) axis

    The 'figure' parameter should contain a figure with vertical and horizontal
    axis text. This function finds the index associated with the white gap.
    For example, there should be a gap of all white pixels between the black
    pixels of the vertical axis text and the black pixels associated with the
    numbers of the y-axis tick marks. This function aims to find the index
    associated with the gap of white pixels. The results of this function can
    then be used to trim the axis from the figure.

    Parameters
    ----------
    figure : numpy.ndarray
        Image of interest

    Returns
    -------
    int
        Index of white gap
    """
    figure = convert_bw(figure, 150)
    is_white_line = True
    # starting from the left of the image, vertically interate over pixels
    # stop when the vertical line contains a non-white pixel
    # will use the y_coor (vertical line) in next step
    for y_coor in range(figure.shape[1]):
        for x_coor in range(figure.shape[0] - 1):
            if figure[x_coor, y_coor] != 255:
                is_white_line = False
                break
        if not is_white_line:
            break
    # starting from the previous step, vertically interate over pixels
    # stop when the vertical line contains only white pixels
    for y_coor_2 in range(y_coor, figure.shape[1] - 1):
        for x_coor_2 in range(figure.shape[0] - 1):
            is_white_line = True
            if figure[x_coor_2, y_coor_2] != 255:
                is_white_line = False
                break
        if is_white_line:
            break

    return y_coor_2 + 1


def get_dim_inds(perp_dim, num_points):
    """Determine indices which evenly divide the length of a dimension

    Given n num_points, this function will return the indices where length of
    perp_dim is roughly evenly divided into n+1 sections

    Parameters
    ----------
    perp_dim : int
        Length of the perpendicular axis of interest
    num_points : int
        Number of points to divide the dimension into

    Returns
    -------
    list of int
        Indices with roughly even distance between
    """
    dim_loc = int(perp_dim/(num_points+1))
    dim_inds = []
    for i in range(1, (num_points+1)):
        dim_inds.append(i * dim_loc)

    return dim_inds


def get_axis_val(spiro_fig_wo_text, num_axis_ind, horizontal=True):
    """Get first and last numbers of figure axis

    Function takes extracts the axis numbers image from the figure, converts
    the image to a string, and returns the first and last numbers of the string

    Parameters
    ----------
    spiro_fig_wo_text : numpy.ndarray
        Spiroware figure which does not contain axis text
    num_axis_ind : int
        Index indicating where the white gap is between the numbers of the axis
        and the ticks of the axis
    horizontal : bool, optional
        Indicates of the axis is horizontal or vertical; vertical axis will
        need to be rotated, by default True

    Returns
    -------
    axis_num_first : int
        First number extracted from the axis image
    axis_num_last : int
        Last number extracted from the axis image
    """

    if horizontal:
        num_axis = spiro_fig_wo_text[num_axis_ind:, :]
        custom_config = (
            r'-l eng --oem 3 --psm 6 -c tessedit_char_whitelist=0123456789 '
        )
    else:
        num_axis = cv2.rotate(
            spiro_fig_wo_text[:, :num_axis_ind], cv2.cv2.ROTATE_90_CLOCKWISE
        )
        custom_config = (
            r'-l eng --oem 3 --psm 6 -c tessedit_char_whitelist=0123456789- '
        )

    axis_text = pytesseract.image_to_string(num_axis, config=custom_config)

    if not horizontal:
        # find first number in string if concatenated; assumes numbers end in 0
        # remove all digits after 0 in case numbers are a single string
        axis_num_first = re.sub('0[^0].*$', '0', axis_text.split()[0])
    else:
        axis_num_first = 0

    # find last number in string if concatenated; assumes numbers end in 0
    non_zero = False
    axis_num_last_rev = ''

    # get last digit and reverse
    for i in axis_text.split()[-1][::-1]:
        if (i in ['0', '-', ' ']) and non_zero:
            break
        elif i != '0':
            non_zero = True
            axis_num_last_rev = axis_num_last_rev + i
        else:
            axis_num_last_rev = axis_num_last_rev + i
    axis_num_last = axis_num_last_rev[::-1]

    return axis_num_first, axis_num_last


def get_left_grid_ind(fig_wo_axis, num_points):
    """Determines the index of the left most grid line

    Function will horizontally iterate over the figure image at n num_points
    and stops once the left most grid line is found. The left most index will
    be associated with a numerical value (i.e. first number in the horizontal
    axis) and processed using plotdigitizer.

    Parameters
    ----------
    fig_wo_axis : numpy.ndarray
        Spiroware figure which does not contain axis text
    num_points : _type_
        The number of points used to try and detect the index, increasing the
        number of points will increase the confidence in the result but will
        increase computation time

    Returns
    -------
    int
        Index of the left most grid line
    """
    (ver_dim, hor_dim, _) = fig_wo_axis.shape
    dim_inds = get_dim_inds(ver_dim, num_points)

    grid_value_ind = []
    for dim_ind in dim_inds:
        # horizontally iterate over figure, starting from the left
        for opp_ind in range(hor_dim):
            # compare value to gray rgb associated with gridlines;
            # stop if gridline found
            if fig_wo_axis[dim_ind, opp_ind, :].tolist() in gray_list:
                if opp_ind != (hor_dim-1):
                    grid_value_ind.append(opp_ind)
                break

    return np.median(grid_value_ind)


def get_right_grid_ind(fig_wo_axis, num_points):
    """Determines the index of the right most grid line

    Function will horizontally iterate over the figure image at n num_points
    and stops once the right most grid line is found. The right most index will
    be associated with a numerical value (i.e. last number in the horizontal
    axis) and processed using plotdigitizer.

    Parameters
    ----------
    fig_wo_axis : numpy.ndarray
        Spiroware figure which does not contain axis text
    num_points : _type_
        The number of points used to try and detect the index, increasing the
        number of points will increase the confidence in the result but will
        increase computation time

    Returns
    -------
    int
        Index of the right most grid line
    """
    (ver_dim, hor_dim, _) = fig_wo_axis.shape
    dim_inds = get_dim_inds(ver_dim, num_points)

    grid_value_ind = []
    for dim_ind in dim_inds:
        # horizontally iterate over figure, starting from the right
        for opp_ind in range(hor_dim-1, 0, -1):
            # compare value to gray rgb associated with gridlines;
            # stop if gridline found
            if fig_wo_axis[dim_ind, opp_ind, :].tolist() in gray_list:
                if opp_ind != 0:
                    grid_value_ind.append(opp_ind)
                break

    return np.median(grid_value_ind)


def get_top_grid_ind(fig_wo_axis, num_points):
    """Determines the index of the top most grid line

    Function will vertically iterate over the figure image at n num_points
    and stops once the top most grid line is found. The top most index will
    be associated with a numerical value (i.e. last number in the vertical
    axis) and processed using plotdigitizer.

    Parameters
    ----------
    fig_wo_axis : numpy.ndarray
        Spiroware figure which does not contain axis text
    num_points : _type_
        The number of points used to try and detect the index, increasing the
        number of points will increase the confidence in the result but will
        increase computation time

    Returns
    -------
    int
        Index of the top most grid line
    """
    (ver_dim, hor_dim, _) = fig_wo_axis.shape
    dim_inds = get_dim_inds(hor_dim, num_points)

    grid_value_ind = []
    for dim_ind in dim_inds:
        # compare value to gray rgb associated with gridlines;
        # stop if gridline found
        for opp_ind in range(ver_dim):
            if fig_wo_axis[opp_ind, dim_ind, :].tolist() in gray_list:
                if opp_ind != 0:
                    grid_value_ind.append(opp_ind)
                break

    # axis is inverted when entering into plotdigitizer
    return ver_dim - np.median(grid_value_ind)


def get_bottom_grid_ind(fig_wo_axis, num_points):
    """Determines the index of the bottom most grid line

    Function will vertically iterate over the figure image at n num_points
    and stops once the bottom most grid line is found. The bottom most index will
    be associated with a numerical value (i.e. first number in the vertical
    axis) and processed using plotdigitizer.

    Parameters
    ----------
    fig_wo_axis : numpy.ndarray
        Spiroware figure which does not contain axis text
    num_points : _type_
        The number of points used to try and detect the index, increasing the
        number of points will increase the confidence in the result but will
        increase computation time

    Returns
    -------
    int
        Index of the bottom most grid line
    """
    (ver_dim, hor_dim, _) = fig_wo_axis.shape
    dim_inds = get_dim_inds(hor_dim, num_points)

    grid_value_ind = []
    for dim_ind in dim_inds:
        for opp_ind in range(ver_dim-1, 0, -1):
            # compare value to gray rgb associated with gridlines;
            # stop if gridline found
            if fig_wo_axis[opp_ind, dim_ind, :].tolist() in gray_list:
                if opp_ind != (ver_dim-1):
                    grid_value_ind.append(opp_ind)
                break

    # axis is inverted when entering into plotdigitizer
    return ver_dim - np.median(grid_value_ind)


def plotdigitizer_digitize(
    img_path, output_path,
    hor_num_first, hor_num_last, ver_num_last, ver_num_first,
    left_grid_ind, right_grid_ind, top_grid_ind, bottom_grid_ind
):
    """Python process plotdigitizer

    This function allows for processing in Python as plotdigitizer was
    originally meant for the command line.

    Notes
    -----
    Based on https://opensource.com/article/21/8/python-argparse

    Parameters
    ----------
    img_path : str
        Path to image
    output_path : str
        Path to save results of plotdigitizer
    hor_num_first : int
        First number extracted from the horiztonal axis image
    hor_num_last : int
        Last number extracted from the horiztonal axis image
    ver_num_last : int
        Last number extracted from the vertical axis image
    ver_num_first : int
        First number extracted from the vertical axis image
    left_grid_ind : int
        Index of the left most grid line
    right_grid_ind : int
        Index of the right most grid line
    top_grid_ind : int
        Index of the top most grid line
    bottom_grid_ind : int
        Index of the bottom most grid line
    """
    # parser arguments are modified from plotdigitizer.plotdigitizer.main
    parser = argparse.ArgumentParser()
    parser.add_argument("INPUT", type=pathlib.Path)
    parser.add_argument("--data-point", "-p", required=True, action="append")
    parser.add_argument("--location", "-l", required=False, action="append")
    parser.add_argument("--plot", required=False)
    parser.add_argument("--output", "-o", required=False, type=str)
    parser.add_argument("--preprocess", required=False, action="store_true")
    parser.add_argument("--debug", required=False, action="store_true")

    value = parser.parse_args([
        img_path,
        '-p', '{},{}'.format(str(hor_num_first), str(ver_num_last)),
        '-p', '{},{}'.format(str(hor_num_first), str(ver_num_first)),
        '-p', '{},{}'.format(str(hor_num_last), str(ver_num_first)),
        '-l', '{},{}'.format(str(left_grid_ind), str(top_grid_ind)),
        '-l', '{},{}'.format(str(left_grid_ind), str(bottom_grid_ind)),
        '-l', '{},{}'.format(str(right_grid_ind), str(bottom_grid_ind)),
        '--output',
        output_path,
        '--preprocess'
    ])

    try:
        plotdigitizer.plotdigitizer.run(value)
    except AssertionError:
        # plotdigitizer will raise AssertionError: Could not read meaningful data
        # if figure is all white; write an empty csv file as a result
        with open(output_path, "w") as my_empty_csv:
            pass


def ver_abs_num_checks(ver_num_first, ver_num_last):
    """Logic checks on vertical absolute axis values

    Parameters
    ----------
    ver_num_first : int
        First number extracted from the vertical axis image
    ver_num_last : int
        Last number extracted from the vertical axis image

    Returns
    -------
    ver_num_first : int
        First number extracted from the vertical axis image that conforms to
        data checks
    ver_num_last : int
        Last number extracted from the vertical axis image that conforms to
        data checks
    """
    # max value under 100 but greater than 0; truncated last digit
    if ((int(ver_num_last) <= 100) and (int(ver_num_last) > 0)):
        ver_num_last = '{}0'.format(ver_num_last)

    # max value over 10000 and last 5 digits are zero; remove last digit
    if (
        (int(ver_num_last) >= 100000)
        and (ver_num_last[-5:] == '00000')
    ):
        while ver_num_last[-5:] == '00000':
            ver_num_last = ver_num_last[:-1]
    # max value over 100000; take last 5 digits
    if (
        (int(ver_num_last) >= 100000)
    ):
        ver_num_last = ver_num_last[-5:]

    # remove negative if last value is negative
    if (
        (int(ver_num_last) < 0)
    ):
        ver_num_last = ver_num_last[1:]

    # add negative if first value is greater than 0
    if (
        (int(ver_num_first) > 0)
    ):
        ver_num_first = '-{}'.format(ver_num_first)

    # min value under -10000 and last 4 digits are zero; remove last digit
    if (
        (int(ver_num_first) <= -100000)
        and (ver_num_first[-5:] == '00000')
    ):
        while ver_num_first[-5:] == '00000':
            ver_num_first = ver_num_first[:-1]

    # min value under -99999; take last 5 digits
    if (
        (int(ver_num_first) <= -100000)
    ):
        ver_num_last = ver_num_last[-5:]

    return ver_num_first, ver_num_last


def ver_rel_num_checks(ver_num_first, ver_num_last):
    """Logic checks on vertical relative axis values

    Parameters
    ----------
    ver_num_first : int
        First number extracted from the vertical axis image
    ver_num_last : int
        Last number extracted from the vertical axis image

    Returns
    -------
    ver_num_first : int
        First number extracted from the vertical axis image that conforms to
        data checks
    ver_num_last : int
        Last number extracted from the vertical axis image that conforms to
        data checks
    """
    # max percentage value over 1000
    if (
        (int(ver_num_last) >= 1000)
    ):
        ver_num_last = ver_num_last[:-1]

    # remove negative from negative percentage
    if (
        (int(ver_num_last) < 0)
    ):
        ver_num_last = ver_num_last[1:]

    # remove negative from negative percentage
    if (
        (int(ver_num_first) < 0)
    ):
        ver_num_first = ver_num_first[1:]

    return ver_num_first, ver_num_last


def hor_num_checks(hor_num_last):
    """Logic checks on horizontal axis values

    Parameters
    ----------
    hor_num_last : int
        Last number extracted from the horizontal axis image

    Returns
    -------
    int
        Last number extracted from the horizontal axis image that conforms to
        data checks
    """
    if(
        (int(hor_num_last) < 0)
    ):
        hor_num_last = hor_num_last[1:]

    return hor_num_last


def mod_axis_num(stat_ind, stat_num, mod_ind, mod_num, new_ind):
    """Modify axis number

    Plotdigitizer does not evaulate data outside the indices it is given. This
    function get recalculates values at the edges of the figure so all data
    is evaluated.

    Parameters
    ----------
    stat_ind : int
        Index of stationary axis (i.e. not modified by this function)
    stat_num : int
        Value associated with stationary axis
    mod_ind : int
        Index of axis to be modified
    mod_num : int
        Value associated with modified axis
    new_ind : int
        New value of axis index

    Returns
    -------
    int
        Recalculated first number of the vertical axis
    """
    delta_ind = float(stat_ind) - float(mod_ind)
    delta_num = float(stat_num) - float(mod_num)
    ind_num_ratio = delta_ind/delta_num
    new_num = float(mod_num) - (float(mod_ind) - float(new_ind))/ind_num_ratio

    return str(new_num)


def main():
    digitize_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../../data/raw/digitize_screenshots'
    ))
    spiroware_screenshots_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../../data/raw/spiroware_screenshots'
    ))

    # get list of all screenshots
    spiroware_screenshots = []
    for (_, _, filenames) in os.walk(spiroware_screenshots_path):
        spiroware_screenshots.extend(filenames)
        break

    # get list of all screenshots digitized
    completed_digits = []
    for (_, _, filenames) in os.walk(digitize_path):
        completed_digits.extend(filenames)
        break
    completed_digits = [
        re.sub('.csv', '', fname) for fname in completed_digits
    ]

    # spiroware_screenshots contains all screenshots not digitized
    spiroware_screenshots = [
        fname
        for fname in spiroware_screenshots
        if re.sub('.png', '', fname) not in completed_digits
    ]

    # corner images are used as landmarks for cropping purposes
    corner_imgs = {
        'co2': {
            'bottom_left': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/co2_bottom_left.png'
            )),
            'top_right': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/co2_top_right.png'
            )),
        },
        'flow': {
            'bottom_left': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/flow_bottom_left.png')
            ),
            'top_right': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/flow_top_right.png')
            ),
        },
        'n2': {
            'bottom_left': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/n2_bottom_left.png')
            ),
            'top_right': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/n2_top_right.png')
            ),
        },
        'o2': {
            'bottom_left': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/o2_bottom_left.png')
            ),
            'top_right': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/o2_top_right.png')
            ),
        },
        'volume': {
            'bottom_left': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/volume_bottom_left.png')
            ),
            'top_right': cv2.imread(os.path.join(
                os.path.dirname(__file__), 'assets/volume_top_right.png')
            ),
        }
    }

    for spiroware_screenshot in spiroware_screenshots:
        print(spiroware_screenshot)
        file_no_path = re.sub(r'\.png', '', spiroware_screenshot)

        screenshot_type = re.sub('.*_', '', spiroware_screenshot)
        screenshot_type = re.sub(r'\.png', '', screenshot_type)

        spiroware_screenshot = cv2.imread(os.path.join(
            spiroware_screenshots_path, spiroware_screenshot
        ))

        spiro_fig = crop_screenshot(
            spiroware_screenshot,
            corner_imgs[screenshot_type]['bottom_left'],
            corner_imgs[screenshot_type]['top_right']
        )

        # remove horizontal and vertical text
        spiro_fig_wo_text = spiro_fig[
            :hor_char_row_ind(spiro_fig), ver_char_row_ind(spiro_fig):
        ]
        # remove horizontal and vertical numerical values
        # save for OCR
        ver_num_axis_ind = ver_char_row_ind(spiro_fig_wo_text)
        hor_num_axis_ind = hor_char_row_ind(spiro_fig_wo_text)

        ver_num_first, ver_num_last = get_axis_val(
            spiro_fig_wo_text, ver_num_axis_ind, False
        )

        if (screenshot_type in ['flow', 'volume']):
            ver_num_first, ver_num_last = ver_abs_num_checks(
                ver_num_first, ver_num_last
            )
        else:
            ver_num_first, ver_num_last = ver_rel_num_checks(
                ver_num_first, ver_num_last
            )

        # horizontal number first is assumed to be 0
        _, hor_num_last = get_axis_val(
            spiro_fig_wo_text, hor_num_axis_ind, True
        )
        hor_num_last = hor_num_checks(hor_num_last)

        # remove axes
        spiro_fig_wo_axes = spiro_fig_wo_text[
            :hor_num_axis_ind, ver_num_axis_ind:
        ]
        # temporary resize due to plotdigitize not picking up points
        spiro_fig_wo_axes_rz = cv2.resize(
            spiro_fig_wo_axes, (0, 0), fx=7, fy=2,
            interpolation=cv2.INTER_NEAREST
        )

        # use figure in colour to distinguish between data points and grid lines
        top_grid_ind = get_top_grid_ind(spiro_fig_wo_axes_rz, 75)
        bottom_grid_ind = get_bottom_grid_ind(spiro_fig_wo_axes_rz, 75)
        left_grid_ind = get_left_grid_ind(spiro_fig_wo_axes_rz, 75)
        right_grid_ind = get_right_grid_ind(spiro_fig_wo_axes_rz, 75)

        # plotdigitizer does not evaulate data outside the indices it is given
        # get values at the edges of the figure so all data is evaluated
        # co2 values don't go to 0 when using the mod_axis_num due to rounding
        if screenshot_type != 'co2':
            ver_num_first = mod_axis_num(
                top_grid_ind, ver_num_last,
                bottom_grid_ind, ver_num_first, 0
            )
            bottom_grid_ind = 0

        # create a temporary file that will be digitized by plotdigitizer
        cv2.imwrite(
            os.path.join(digitize_path, 'temp_fig_file.png'),
            convert_bw(spiro_fig_wo_axes_rz)
        )

        # digitize black and white figure
        plotdigitizer_digitize(
            os.path.join(digitize_path, 'temp_fig_file.png'),
            os.path.join(digitize_path, '{}.csv'.format(file_no_path)),
            0, hor_num_last, ver_num_last, ver_num_first,
            left_grid_ind, right_grid_ind, top_grid_ind, bottom_grid_ind
        )


if __name__ == "__main__":
    main()
