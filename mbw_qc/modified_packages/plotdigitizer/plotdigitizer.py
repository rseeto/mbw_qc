__author__ = "Dilawar Singh"
__copyright__ = "Copyright 2017-, Dilawar Singh"
__maintainer__ = "Dilawar Singh"
__email__ = "dilawar.s.rajput@gmail.com"
__status__ = "Development"

import typing as T
import tempfile
import hashlib
from pathlib import Path

import cv2 as cv
import numpy as np
import numpy.polynomial.polynomial as poly

import plotdigitizer.grid as grid
import plotdigitizer.trajectory as trajectory
import plotdigitizer.geometry as geometry

#
# Logger
#
import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING")

logger.add(
    Path(tempfile.gettempdir()) / "plotdigitizer.log", level="DEBUG", rotation="10MB"
)

WindowName_ = "PlotDigitizer"
ix_, iy_ = 0, 0
params_: T.Dict[str, T.Any] = {}

args_: T.Optional[T.Any] = None

# NOTE: remember these are cv coordinates and not numpy.
locations_: T.List[geometry.Point] = []
points_: T.List[geometry.Point] = []

img_: np.ndarray = np.zeros((1, 1))


def cache() -> Path:
    c = Path(tempfile.gettempdir()) / "plotdigitizer"
    c.mkdir(parents=True, exist_ok=True)
    return c


def data_to_hash(data) -> str:
    return hashlib.sha1(data).hexdigest()


def save_img_in_cache(img: np.ndarray, filename: T.Optional[T.Union[Path, str]] = None):
    if filename is None:
        filename = Path(f"{data_to_hash(img)}.png")
    outpath = cache() / filename
    cv.imwrite(str(outpath), img)
    logger.debug(f" Saved to {outpath}")


def plot_traj(traj, outfile: Path):
    global locations_
    import matplotlib.pyplot as plt

    x, y = zip(*traj)
    plt.figure()
    plt.subplot(211)

    for p in locations_:
        csize = img_.shape[0] // 40
        cv.circle(img_, (p.x, img_.shape[0] - p.y), csize, 128, -1)

    plt.imshow(img_, interpolation="none", cmap="gray")
    plt.axis(False)
    plt.title("Original")
    plt.subplot(212)
    plt.title("Reconstructed")
    plt.plot(x, y)
    plt.tight_layout()
    if not str(outfile):
        plt.show()
    else:
        plt.savefig(outfile)
        logger.info(f"Saved to {outfile}")
    plt.close()


def click_points(event, x, y, flags, params):
    global img_
    assert img_ is not None, "No data set"
    # Function to record the clicks.
    YROWS = img_.shape[0]
    if event == cv.EVENT_LBUTTONDOWN:
        logger.info(f"You clicked on {(x, YROWS-y)}")
        locations_.append(geometry.Point(x, YROWS - y))


def show_frame(img, msg="MSG: "):
    global WindowName_
    msgImg = np.zeros(shape=(50, img.shape[1]))
    cv.putText(msgImg, msg, (1, 40), 0, 0.5, 255)
    newImg = np.vstack((img, msgImg.astype(np.uint8)))
    cv.imshow(WindowName_, newImg)


def ask_user_to_locate_points(points, img):
    global locations_
    cv.namedWindow(WindowName_)
    cv.setMouseCallback(WindowName_, click_points)
    while len(locations_) < len(points):
        i = len(locations_)
        p = points[i]
        pLeft = len(points) - len(locations_)
        show_frame(img, "Please click on %s (%d left)" % (p, pLeft))
        if len(locations_) == len(points):
            break
        key = cv.waitKey(1) & 0xFF
        if key == "q":
            break
    logger.info("You clicked %s" % locations_)


def list_to_points(points) -> T.List[geometry.Point]:
    ps = [geometry.Point.fromCSV(x) for x in points]
    return ps


def axis_transformation(p, P: T.List[geometry.Point]):
    """Compute m and offset for model Y = m X + offset that is used to transform
    axis X to Y"""

    # Currently only linear maps and only 2D.
    px, py = zip(*p)
    Px, Py = zip(*P)
    offX, sX = poly.polyfit(px, Px, 1)
    offY, sY = poly.polyfit(py, Py, 1)
    return ((sX, sY), (offX, offY))


def transform_axis(img, erase_near_axis: int = 0):
    global locations_
    global points_
    # extra: extra rows and cols to erase. Help in containing error near axis.
    # compute the transformation between old and new axis.
    T = axis_transformation(points_, locations_)
    p = geometry.find_origin(locations_)
    offCols, offRows = p.x, p.y
    logger.info(f"{locations_} → origin {offCols}, {offRows}")
    img[:, : offCols + erase_near_axis] = params_["background"]
    img[-offRows - erase_near_axis :, :] = params_["background"]
    logger.debug(f"Tranformation params: {T}")
    return T


def _find_trajectory_colors(img, plot: bool = False) -> T.Tuple[int, T.List[int]]:
    # Each trajectory color x is bounded in the range x-3 to x+2 (interval of
    # 5) -> total 51 bins. Also it is very unlikely that colors which are too
    # close to each other are part of different trajecotries. It is safe to
    # assme a binwidth of at least 10px.
    hs, bs = np.histogram(img.ravel(), 255 // 10, [0, img.max()])

    # Now a trajectory is only trajectory if number of pixels close to the
    # width of the image (we are using at least 75% of width).
    # hs[hs < img.shape[1] * 3 // 4] = 0
    # Ryan Note 07MAR2022: previously returning no value; 
    # change ratio from 3/4 to 1/8
    hs[hs < img.shape[1] * 1 // 8] = 0

    if plot:
        import matplotlib.pyplot as plt

        plt.figure()
        plt.bar(bs[:-1], np.log(hs))
        plt.xlabel("color")
        plt.ylabel("log(#pixel)")
        plt.show()

    # background is usually the color which is most count. We can find it
    # easily by sorting the histogram.
    hist = sorted(zip(hs, bs), reverse=True)

    # background is the most occuring pixel value.
    bgcolor = int(hist[0][1])

    # we assume that bgcolor is close to white.
    if bgcolor < 128:
        logger.error(
            "I computed that background is 'dark' which is unacceptable to me."
        )
        quit(-1)

    # If the background is white, search from the trajectories from the black.
    trajcolors = [int(b) for h, b in hist if h > 0 and b / bgcolor < 0.5]
    return bgcolor, trajcolors


def compute_foregrond_background_stats(img) -> T.Dict[str, float]:
    """Compute foreground and background color."""
    params: T.Dict[str, T.Any] = {}
    # Compute the histogram. It should be a multimodal histogram. Find peaks
    # and these are the colors of background and foregorunds. Currently
    # implementation is very simple.
    bgcolor, trajcolors = _find_trajectory_colors(img)
    params["background"] = bgcolor
    params["timeseries_colors"] = trajcolors
    logger.info(f" computed parameters: {params}")
    return params


def process_image(img):
    global params_
    global args_
    params_ = compute_foregrond_background_stats(img)

    T = transform_axis(img, erase_near_axis=3)
    assert img.std() > 0.0, "No data in image"
    # logger.info(f" {img.mean()}  {img.std()}")
    save_img_in_cache(img, f"{args_.INPUT.name}.transformed_axis.png")

    # extract the plot that has color which is farthest from the background.
    trajcolor = params_["timeseries_colors"][0]
    traj, img = trajectory.find_trajectory(img, trajcolor, T)
    save_img_in_cache(img, f"{args_.INPUT.name}.final.png")
    return traj


def run(args):
    global locations_, points_
    global img_, args_
    args_ = args

    infile = Path(args.INPUT)
    assert infile.exists(), f"{infile} does not exists."
    logger.info(f"Extracting trajectories from {infile}")

    img_ = cv.imread(str(infile), 0)

    # rescale.
    img_ = img_ - img_.min()
    img_ = (255 * (img_ / img_.max())).astype(np.uint8)

    assert img_.max() <= 255
    assert img_.min() < img_.mean() < img_.max(), "Could not read meaningful data"

    save_img_in_cache(img_, args_.INPUT.name)

    points_ = list_to_points(args.data_point)
    locations_ = list_to_points(args.location)
    logger.debug(f"data points {args.data_point} → location on image {args.location}")

    if len(locations_) != len(points_):
        logger.warning(
            "Either the location of data-points are not specified or their numbers don't"
            " match with given datapoints. Asking user..."
        )
        ask_user_to_locate_points(points_, img_)

    # erosion after dilation (closes gaps)
    if args_.preprocess:

        kernel = np.ones((1, 1), np.uint8)
        img_ = cv.morphologyEx(img_, cv.MORPH_CLOSE, kernel)
        save_img_in_cache(img_, Path(f"{args_.INPUT.name}.close.png"))

    # remove grids.
    # Ryan Note 02MAR2022: Comment out remove gridlines since converting to bw
    # deals with this
    # img_ = grid.remove_grid(img_)
    save_img_in_cache(img_, Path(f"{args_.INPUT.name}.without_grid.png"))

    traj = process_image(img_)

    if args_.plot is not None:
        plot_traj(traj, args_.plot)

    outfile = args.output or "%s.traj.csv" % args.INPUT
    with open(outfile, "w") as f:
        for r in traj:
            f.write("%g %g\n" % (r))
    logger.info("Wrote trajectory to %s" % outfile)


def main():
    # Argument parser.
    import argparse

    description = """Digitize image."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("INPUT", type=Path, help="Input image file.")
    parser.add_argument(
        "--data-point",
        "-p",
        required=True,
        action="append",
        help="Datapoints (min 3 required). You have to click on them later."
        " At least 3 points are recommended. e.g -p 0,0 -p 10,0 -p 0,1 "
        "Make sure that point are comma separated without any space.",
    )
    parser.add_argument(
        "--location",
        "-l",
        required=False,
        default=[],
        action="append",
        help="Location of a points on figure in pixels (integer)."
        " These values should appear in the same order as -p option."
        " If not given, you will be asked to click on the figure.",
    )
    parser.add_argument(
        "--plot",
        default=None,
        required=False,
        help="Plot the final result. Requires matplotlib.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        type=str,
        help="Name of the output file else trajectory will be written to "
        " <INPUT>.traj.csv",
    )
    parser.add_argument(
        "--preprocess",
        required=False,
        action="store_true",
        help="Preprocess the image. Useful with bad resolution images.",
    )
    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        help="Enable debug logger",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
