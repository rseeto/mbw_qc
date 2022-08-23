"""Script to confirm there are no issues with Spiroware screenshots"""

import os
import re
import cv2
import pytesseract


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
    figure_bw = cv2.threshold(
        figure_gray, threshold, 255, cv2.THRESH_BINARY
    )[1]

    return figure_bw


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
    # starting from the bottom of the image, horizontally interate over pixels
    # stop when the horizontal line contains a non-white pixel
    # will use the x_coor (horizontal line) in next step
    for y_coor in range(figure.shape[1]):
        for x_coor in range(figure.shape[0] - 1):
            if figure[x_coor, y_coor] != 255:
                is_white_line = False
                break
        if not is_white_line:
            break
    # starting from the previous step, horizontally interate over pixels
    # stop when the horizontal line contains only white pixels
    for y_coor_2 in range(y_coor, figure.shape[1] - 1):
        for x_coor_2 in range(figure.shape[0] - 1):
            is_white_line = True
            if figure[x_coor_2, y_coor_2] != 255:
                is_white_line = False
                break
        if is_white_line:
            break

    return y_coor_2 + 1


def main():
    spiroware_screenshots_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../../data/raw/spiroware_screenshots'
    ))

    spiroware_screenshots = []
    for (_, _, filenames) in os.walk(spiroware_screenshots_path):
        spiroware_screenshots.extend(filenames)
        break

    # corner images are used as landmarks for cropping purposes
    corner_imgs = {
        'co2': {
            'bottom_left': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/co2_bottom_left.png'
            ))),
            'top_right': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/co2_top_right.png'
            ))),
        },
        'flow': {
            'bottom_left': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/flow_bottom_left.png'
            ))),
            'top_right': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/flow_top_right.png'
            ))),
        },
        'n2': {
            'bottom_left': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/n2_bottom_left.png'
            ))),
            'top_right': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/n2_top_right.png'
            ))),
        },
        'o2': {
            'bottom_left': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/o2_bottom_left.png'
            ))),
            'top_right': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/o2_top_right.png'
            ))),
        },
        'volume': {
            'bottom_left': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/volume_bottom_left.png'
            ))),
            'top_right': cv2.imread(os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../features/assets/volume_top_right.png'
            ))),
        }
    }

    expected_text = {
        'co2': 'CO2[%]',
        'flow': 'Flow[ml/s]',
        'n2': 'N2[%]',
        'o2': 'O2[%]',
        'volume': 'Vol.[ml]'
    }

    for spiroware_screenshot in spiroware_screenshots:
        spiroware_screenshot_fname = spiroware_screenshot

        screenshot_type = re.sub('.*_', '', spiroware_screenshot)
        screenshot_type = re.sub(r'\.png', '', screenshot_type)
        try:
            spiroware_screenshot = cv2.imread(os.path.abspath(os.path.join(
                spiroware_screenshots_path, spiroware_screenshot
            )))

            spiro_fig = crop_screenshot(
                spiroware_screenshot,
                corner_imgs[screenshot_type]['bottom_left'],
                corner_imgs[screenshot_type]['top_right']
            )

            # preprocess vertical axis before digitizing by rotating 90
            num_axis = cv2.rotate(
                spiro_fig[:, :ver_char_row_ind(spiro_fig)],
                cv2.cv2.ROTATE_90_CLOCKWISE
            )

            # convert the axis text image into a string
            custom_config = (
                r'-l eng --oem 3 --psm 6 -c '
                + r'tessedit_char_whitelist=Flow[ml/s]N2[%]CO2[%]Vol.[ml]O2[%]'
            )
            axis_text = pytesseract.image_to_string(
                num_axis, config=custom_config
            )
            axis_text = re.sub('\n', '', axis_text)

            # compare the axis text string to the expected text
            # (based on screenshot type); print if string is not as expected so
            # image can be followed up
            if axis_text != expected_text[screenshot_type]:
                print(spiroware_screenshot_fname)
        except Exception as e:
            print('Image issue: ' + spiroware_screenshot_fname)


if __name__ == "__main__":
    main()
