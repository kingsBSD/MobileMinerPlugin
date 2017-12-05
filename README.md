MobileMinerPlugin
=================

This is a [CKAN](https://ckan.org/) extension to recieve data from the [MobileMiner](https://github.com/kingsBSD/MobileMiner) Android app. 
It's no longer under active deployment or development, and was written for the
["Our Data, Ourselves" project](https://big-social-data.net/about/) at King's College London's
[Department of Digital Humanities](https://www.kcl.ac.uk/artshums/depts/ddh/index.aspx).

It takes network socket data on a per-app basis and aggregates it to produce a diary of daily usage. Cell-tower traces spatially resolved via
[OpenCellID](https://opencellid.org/) are clustered by k-means using scikit-learn. It was used to return the data it collected from
our [Young Rewired State participants](https://twitter.com/youngrewired) at a
[hackathon](https://big-social-data.net/2015/01/10/a-long-overdue-updates-on-the-success-of-our-second-hackathon/).
You can read more about the data it collected and what was done with it in:

- [Mining Mobile Youth Cultures](https://bigsocialdata.files.wordpress.com/2015/02/blanke-big-humanities-2014.pdf) at
[The Second IEEE Big Data 2014 Workshop](https://bighumanities.net/events/ieee-bigdata-oct-2014/big-humanities-data-workshop-program/)
([2014 IEEE International Conference on Big Data](http://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=6973861))
- [Research on Online Digital Cultures - Community Extraction and Analysis by Markov and k-Means Clustering](http://kdd.isti.cnr.it/pap2017/papers/PAP_2017_paper_3.pdf) at the [1st International Workshop on Personal Analytics and Privacy](http://kdd.isti.cnr.it/pap2017/)
([2017 European Conference on Machine Learning](http://ecmlpkdd2017.ijs.si/))

This research was also [presented](https://youtu.be/hjjniizB794)
([slides](https://www.slideshare.net/kingsBSD/pydata-2015-odo)) at the [2015 PyData London Conference](https://pydata.org/london2015/):

[![Our Data, Ourselves](https://img.youtube.com/vi/hjjniizB794/0.jpg)](https://youtu.be/hjjniizB794)

Some apps were observed to "phone home" so aggresively that a [containerized suite of tools](https://github.com/kingsBSD/DroidDestructionKit) to
teach novices Android app reversal and network traffic analysis was developed, but that's [another story](https://www.slideshare.net/kingsBSD/droid-hacking-for-the-innocent). 


