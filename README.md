# opinionated-reporting
A reporting framework for that runs on django

My opinion is that a reporting system requires data to be normalized differently than an operational/transactional system
in order for either to remain performant. You can optimize operational systems in many ways that make them very fast. Often
these operations will make any attempt at reporting much slower. While optimizng for reporting can easily make your
operational system slow or difficult to maintain.

The goal of this application is to create a separated data structure optimized for reporting purposes. This frees you,
the developer, up to optimizing your application in any and every way you see fit. While your reporting system comes
for free and optimized. Creating that reporting system should be just as simple as serializing models, or writing
forms for you models. Making this simple to create allow you to focus on creating all the moments and events 
you are trying to report on (the harder it is, the fewer you'll want to track). In my opinion, track everything you
ever think you can want.

## Creating a reporting system with Opinionated Reporting
You will define specific "Facts" that represent a reportable moment in the lifecycle of your operational system.
That moment may be when a order moves from "in checkout" to "completed checkout". That moment may be when a price
on a SKU, or stock ticker, changes. Each of those moments are a different "Fact".

These facts will contain the necessary fields you are tracking. The fields will either be a quantitative value, or
a "Dimension" that is filterable. For instance, the total amount on an order is a quantitative value, while the Customer
that order belongs to (along with any and all of the indentifiable data for a customer) is a "Dimension".


## Example
